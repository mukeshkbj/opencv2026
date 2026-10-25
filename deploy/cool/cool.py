"""Run Twice on Cloud-Optimized OpenCV (COOL) on AWS Graviton4.

  python deploy/cool/cool.py bench    COOL vs pip OpenCV on one Graviton4 instance, plus pip OpenCV on x86.
                                      Instances terminate themselves; results land in docs/eval/cool/.
  python deploy/cool/cool.py serve    The Twice app on a COOL instance, public on port 80. Prints the URL.
  python deploy/cool/cool.py report   Rebuild docs/eval/cool/README.md from the saved results.

Needs boto3, AWS credentials, and a one-time subscription to the COOL Graviton4 AMI in AWS Marketplace.
No SSH key or instance role: code goes up and results come back through presigned S3 URLs.
"""
import argparse
import io
import json
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "eval" / "cool"
MARKETPLACE = "https://aws.amazon.com/marketplace/pp/prodview-fdvbfiewzuehs"
X86_AMI_PARAM = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
# us-east-1 on-demand Linux prices per hour, October 2026, plus the COOL software fee from the Marketplace listing.
PRICE = {"c8g.xlarge": 0.15952, "c8g.2xlarge": 0.31904, "c7i.xlarge": 0.1785, "c7i.2xlarge": 0.357}
COOL_FEE = {"c8g.xlarge": 0.01, "c8g.2xlarge": 0.02}
PIP_OPENCV = "opencv-contrib-python-headless==5.0.0.93"
FIND_COOL = r"""VENV=$(ls -d /opt/cool/venvs/python_3.12 /opt/cool/venvs/python_3.* 2>/dev/null | head -1)
if [ -n "$VENV" ]; then PY=$VENV/bin/python; PIPX=""; else
  export LD_LIBRARY_PATH=/opt/cool/cpp_sdk/lib:$LD_LIBRARY_PATH PYTHONPATH=/opt/cool/python_3.12/site-packages
  PY=python3.12; PIPX="--break-system-packages"; apt-get update -q && apt-get install -y -q python3-pip; fi"""

BENCH_SH = r"""#!/bin/bash
exec > /var/log/twice.log 2>&1
set -x
trap 'curl -s -X PUT --upload-file /var/log/twice.log "@LOG@"; shutdown -h now' EXIT
mkdir -p /opt/twice && cd /opt/twice
curl -sf -o code.tgz "@CODE@" && tar xzf code.tgz && cd server
if [ "@COOL@" = "1" ]; then
  @FIND_COOL@
  $PY -c "import numpy" || $PY -m pip install -q $PIPX numpy
  $PY -c "import cv2; print('COOL cv2', cv2.__version__, cv2.__file__)"
  $PY -m eval.cool_bench --label cool-arm --instance @TYPE@ --out /opt/twice/cool-arm.json \
    && curl -sf -X PUT --upload-file /opt/twice/cool-arm.json "@PUT_COOL@"
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update -q && apt-get install -y -q python3.12-venv
python3.12 -m venv /opt/pipcv && /opt/pipcv/bin/pip install -q @PIP_OPENCV@ numpy
/opt/pipcv/bin/python -m eval.cool_bench --label @PIP_LABEL@ --instance @TYPE@ --out /opt/twice/pip.json \
  && curl -sf -X PUT --upload-file /opt/twice/pip.json "@PUT_PIP@"
"""

SERVE_SH = r"""#!/bin/bash
exec > /var/log/twice.log 2>&1
set -x
mkdir -p /opt/twice/data && cd /opt/twice
curl -sf -o code.tgz "@CODE@" && tar xzf code.tgz && cd server
@FIND_COOL@
grep -viE '^(opencv|numpy)' requirements.txt > /opt/twice/req.txt
$PY -m pip install -q $PIPX -r /opt/twice/req.txt
cat > /etc/systemd/system/twice.service <<EOF
[Unit]
After=network-online.target
[Service]
WorkingDirectory=/opt/twice/server
Environment=TWICE_WEB=/opt/twice/web/dist TWICE_DATA=/opt/twice/data
Environment="PYTHONPATH=$PYTHONPATH" "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
ExecStart=$PY -m uvicorn twice.app:app --host 0.0.0.0 --port 80
Restart=always
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now twice
"""


def bundle(serve: bool) -> bytes:
    keep = ["server/twice", "server/models", "server/eval/scenes"] + [str(p.relative_to(ROOT)) for p in (ROOT / "server" / "eval").glob("*.py")]
    if serve:
        dist = ROOT / "web" / "dist"
        if not (dist / "index.html").exists():
            raise SystemExit("Build the web app first: cd web && npm ci && npm run build")
        keep += ["server/samples", "server/requirements.txt", "web/dist"]
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel in keep:
            tar.add(ROOT / rel, arcname=rel, filter=lambda t: None if "__pycache__" in t.name else t)
    return buf.getvalue()


def cool_ami(ec2, ami: str | None) -> str:
    if ami:
        return ami
    images = ec2.describe_images(Owners=["aws-marketplace"], Filters=[
        {"Name": "name", "Values": ["*OpenCV*"]}, {"Name": "architecture", "Values": ["arm64"]}])["Images"]
    images = [i for i in images if "graviton4" in (i.get("Name", "") + i.get("Description", "")).lower()] or images
    if not images:
        raise SystemExit(f"No COOL AMI found. Subscribe first ({MARKETPLACE}) or pass --ami.")
    best = max(images, key=lambda i: i["CreationDate"])
    print(f"COOL AMI: {best['ImageId']}  {best.get('Name')}")
    return best["ImageId"]


def launch(ec2, ami: str, itype: str, user_data: str, name: str, sg: list[str] | None = None, terminate: bool = True) -> str:
    args = dict(ImageId=ami, InstanceType=itype, MinCount=1, MaxCount=1, UserData=user_data,
                TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": name}]}],
                BlockDeviceMappings=[{"DeviceName": ec2.describe_images(ImageIds=[ami])["Images"][0]["RootDeviceName"],
                                      "Ebs": {"VolumeSize": 30, "VolumeType": "gp3", "DeleteOnTermination": True}}])
    if terminate:
        args["InstanceInitiatedShutdownBehavior"] = "terminate"
    if sg:
        args["SecurityGroupIds"] = sg
    try:
        iid = ec2.run_instances(**args)["Instances"][0]["InstanceId"]
    except ec2.exceptions.ClientError as e:
        if "OptInRequired" in str(e):
            raise SystemExit(f"Accept the COOL subscription first: {MARKETPLACE}") from e
        raise
    print(f"launched {name}: {iid} ({itype})")
    return iid


def bucket_for(session, s3) -> str:
    account = session.client("sts").get_caller_identity()["Account"]
    name = f"twice-cool-{account}-{int(time.time())}"
    region = session.region_name
    s3.create_bucket(Bucket=name, **({} if region == "us-east-1" else {"CreateBucketConfiguration": {"LocationConstraint": region}}))
    return name


def presign(s3, bucket: str, key: str, method: str) -> str:
    return s3.generate_presigned_url(method, Params={"Bucket": bucket, "Key": key}, ExpiresIn=4 * 3600)


def fill(template: str, **values: str) -> str:
    values = {"FIND_COOL": FIND_COOL, **values}
    for k, v in values.items():
        template = template.replace(f"@{k}@", v)
    return template


def bench(args, session) -> None:
    ec2, s3 = session.client("ec2"), session.client("s3")
    arm_ami = cool_ami(ec2, args.ami)
    x86_ami = session.client("ssm").get_parameter(Name=X86_AMI_PARAM)["Parameter"]["Value"]
    bucket = bucket_for(session, s3)
    s3.put_object(Bucket=bucket, Key="code.tgz", Body=bundle(serve=False))
    code = presign(s3, bucket, "code.tgz", "get_object")
    wanted = {"cool-arm": "cool-arm.json", "pip-arm": "pip-arm.json", "pip-x86": "pip-x86.json"}
    put = {k: presign(s3, bucket, v, "put_object") for k, v in wanted.items()}
    runs = [("twice-cool-arm", arm_ami, args.arm_type, "1", "pip-arm"), ("twice-pip-x86", x86_ami, args.x86_type, "0", "pip-x86")]
    ids = []
    try:
        for name, ami, itype, cool, pip_label in runs:
            ids.append(launch(ec2, ami, itype, fill(
                BENCH_SH, CODE=code, COOL=cool, TYPE=itype, PIP_OPENCV=PIP_OPENCV, PIP_LABEL=pip_label,
                PUT_COOL=put["cool-arm"], PUT_PIP=put[pip_label], LOG=presign(s3, bucket, f"{name}.log", "put_object")), name))
        deadline = time.time() + args.minutes * 60
        logs = {"twice-cool-arm.log", "twice-pip-x86.log"}
        while time.time() < deadline:
            keys = {o["Key"] for o in s3.list_objects_v2(Bucket=bucket).get("Contents", [])}
            print(f"{time.strftime('%H:%M:%S')} results: {sorted(k for k in keys if k.endswith('.json'))}", flush=True)
            if logs <= keys:
                break
            time.sleep(30)
        OUT.mkdir(parents=True, exist_ok=True)
        for key in sorted({o["Key"] for o in s3.list_objects_v2(Bucket=bucket).get("Contents", [])} - {"code.tgz"}):
            s3.download_file(bucket, key, str(OUT / key))
            print(f"saved docs/eval/cool/{key}")
    finally:
        if ids:
            ec2.terminate_instances(InstanceIds=ids)
            print(f"terminated {ids}")
        for o in s3.list_objects_v2(Bucket=bucket).get("Contents", []):
            s3.delete_object(Bucket=bucket, Key=o["Key"])
        s3.delete_bucket(Bucket=bucket)
    report()


def serve(args, session) -> None:
    ec2, s3 = session.client("ec2"), session.client("s3")
    ami = cool_ami(ec2, args.ami)
    vpc = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    found = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": ["twice-cool-http"]}, {"Name": "vpc-id", "Values": [vpc]}])["SecurityGroups"]
    if found:
        sg = found[0]["GroupId"]
    else:
        sg = ec2.create_security_group(GroupName="twice-cool-http", Description="Twice on COOL, HTTP", VpcId=vpc)["GroupId"]
        ec2.authorize_security_group_ingress(GroupId=sg, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
    bucket = bucket_for(session, s3)
    s3.put_object(Bucket=bucket, Key="code.tgz", Body=bundle(serve=True))
    iid = launch(ec2, ami, args.arm_type, fill(SERVE_SH, CODE=presign(s3, bucket, "code.tgz", "get_object")),
                 "twice-cool-serve", [sg], terminate=False)
    ec2.get_waiter("instance_running").wait(InstanceIds=[iid])
    ip = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0].get("PublicIpAddress")
    print(f"Twice on COOL: http://{ip}/  (ready in about 3 minutes; http://{ip}/api/health shows opencv_build COOL)")
    print(f"The code bundle stays in s3://{bucket} until the instance has fetched it; delete it after.")
    print(f"Stop it: aws ec2 terminate-instances --instance-ids {iid}")


def row(r: dict, w: dict) -> str:
    itype = r["instance"]
    hourly = PRICE.get(itype, 0) + (COOL_FEE.get(itype, 0) if r["env"]["is_cool"] else 0)
    per_k = f"${hourly / (w['checks_per_s'] * 3600) * 1000:.2f}" if hourly else "n/a"
    return (f"| {r['label']} | {itype} | {r['env']['cpu']} | {w['threads']} | {w['median_ms']:.0f} | {w['p95_ms']:.0f} | "
            f"{w['checks_per_s']:.2f} | {per_k} | {w['recall']:.3f} / {w['precision']:.3f} | `{w['outcome_hash']}` |")


def report() -> None:
    results = {p.stem: json.loads(p.read_text()) for p in sorted(OUT.glob("*.json"))}
    if not results:
        raise SystemExit("No results in docs/eval/cool/. Run: python deploy/cool/cool.py bench")
    lines = ["# COOL benchmark results", "", "Generated by `python deploy/cool/cool.py report` from the JSON files in this folder.", "",
             "## Builds", "", "| Run | OpenCV | Loaded from | COOL | Machine | Python | numpy |", "|---|---|---|---|---|---|---|"]
    for r in results.values():
        e = r["env"]
        lines.append(f"| {r['label']} | {e['cv2_version']} | `{e['cv2_file']}` | {'yes' if e['is_cool'] else 'no'} | {e['machine']} | {e['python']} | {e['numpy']} |")
    lines += ["", "## The Twice check (full agent loop, 36 pairs, follow-up photos included)", "",
              "| Run | Instance | CPU | Threads | Median ms | p95 ms | Checks/s | Cost per 1000 checks | Recall / precision | Outcomes |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in results.values():
        lines += [row(r, w) for w in r["workload"]]
    names = list(next(iter(results.values()))["ops_ms"])
    lines += ["", "## OpenCV calls the check uses (median ms, all threads)", "",
              "| Call | " + " | ".join(results) + " |", "|---" * (len(results) + 1) + "|"]
    for n in names:
        lines.append(f"| {n} | " + " | ".join(f"{r['ops_ms'].get(n, float('nan')):.2f}" for r in results.values()) + " |")
    lines += ["", "## Where a check spends its time (share of wall time, all threads)", ""]
    for label, r in results.items():
        share = ", ".join(f"{k} {v:.0%}" for k, v in r["profile"]["share"].items() if v >= 0.01)
        lines.append(f"- **{label}:** {share}; the rest is numpy, FLANN, DIS flow and Python.")
    lines += ["", "Equal outcome hashes mean every pair ended with the same verdicts and the same follow-up requests.",
              "Cost uses the on-demand price plus the COOL software fee in `deploy/cool/cool.py`; check current prices before quoting."]
    (OUT / "README.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT / 'README.md'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["bench", "serve", "report"])
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--profile")
    ap.add_argument("--ami", help="COOL AMI id, if the Marketplace search does not find it")
    ap.add_argument("--arm-type", default="c8g.xlarge")
    ap.add_argument("--x86-type", default="c7i.xlarge")
    ap.add_argument("--minutes", type=int, default=75, help="give up waiting for results after this long")
    args = ap.parse_args()
    if args.command == "report":
        return report()
    import boto3
    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    (bench if args.command == "bench" else serve)(args, session)


if __name__ == "__main__":
    main()
