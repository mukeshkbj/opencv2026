# Twice on Cloud-Optimized OpenCV (COOL)

**Status:** the benchmark and deployment kit is complete and tested locally with pip OpenCV. It has not run on AWS yet, because the build machine has no AWS credentials. After `python deploy/cool/cool.py bench` runs, the measured results appear in [eval/cool/README.md](eval/cool/README.md). This page claims no COOL speed-up before then.

## What runs on COOL

The claimed core workload is the Twice check: one move-out photo against its move-in photo, through the whole agent loop. That loop covers the SIFT keyframes, FLANN matching, the `USAC_MAGSAC` homography, `warpPerspective`, DIS optical flow, the structure and colour change map, triage, NanoDet on `cv2.dnn.ENGINE_NEW`, and the follow-up photos the agent asks for. The code is the same `server/twice` package that the app serves. Only the OpenCV build underneath changes.

| Item | Value |
|---|---|
| COOL product | Cloud Optimized OpenCV for AWS Graviton4, listing version 3.1, built on OpenCV 5.0 ([AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-fdvbfiewzuehs)) |
| Delivery | AMI, Ubuntu 24.04 LTS, libraries under `/opt/cool`, Python 3.12 virtual environment |
| Instance | `c8g.xlarge` (Graviton4, 4 vCPU), us-east-1. `--arm-type` changes it. |
| Arm baseline | pip `opencv-contrib-python-headless==5.0.0.93` on the same `c8g.xlarge` |
| x86 baseline | pip `opencv-contrib-python-headless==5.0.0.93` on `c7i.xlarge` (4 vCPU), Ubuntu 24.04 |

## Architecture: x86 and Arm side by side

| Where | CPU | OpenCV | Role |
|---|---|---|---|
| Development machine | x86 (Intel Core i9-13900K) | pip 5.0.0 | development, the local benchmarks in `evaluation.md` |
| AWS Lambda behind a Function URL (`deploy/template.yaml`) | Arm, Graviton2 (`arm64`) | pip 5.0.0 wheel in the container | the public app, with S3, KMS and Bedrock |
| EC2 from the COOL AMI (`deploy/cool/cool.py serve`) | Arm, Graviton4 | COOL | the same app on COOL |
| EC2 `c7i.xlarge` (`cool.py bench`) | x86 | pip 5.0.0 | the x86 baseline |

COOL does not go into the Lambda image. It ships as an AMI or as an ECS/EKS container for Graviton4, and its binaries target Neoverse V2 cores. Lambda's `arm64` functions run on Graviton2, so the COOL path runs on EC2. The package does not change: `import cv2` loads COOL when its virtual environment is active, and the pip wheel otherwise. `GET /api/health` reports `"opencv_build": "COOL"` or `"pip"`, together with the CPU architecture.

## Method

`python deploy/cool/cool.py bench` does the whole run without SSH and without an instance role:

1. It packs `server/twice`, the NanoDet model, the benchmark scenes and `server/eval/*.py`, and uploads the bundle to a temporary S3 bucket.
2. It launches two instances. Each one fetches the bundle through a presigned URL:
   - A `c8g.xlarge` from the COOL AMI. It runs `server/eval/cool_bench.py` twice: first with COOL's Python, then with pip OpenCV in a fresh virtual environment. The two runs use the same hardware.
   - A `c7i.xlarge` with Ubuntu 24.04. It runs the benchmark with pip OpenCV.
3. Each instance uploads its JSON result and its log through presigned URLs, then shuts down and terminates itself. The launcher downloads the results into `docs/eval/cool/`, terminates both instances, deletes the bucket and writes `docs/eval/cool/README.md`.

`cool_bench.py` measures five things:

- **The Twice check:** 36 pairs from the agent benchmark, with 6 from each set, follow-up photos included. Each run uses 1 thread and then all threads. It reports the median and 95th-percentile latency, checks per second, recall and precision.
- **Same results:** a hash of every pair's verdicts and follow-up requests. Equal hashes mean that COOL and pip OpenCV made the same decisions.
- **Cost:** the cost per 1000 checks, from the on-demand price plus the COOL software fee ($0.01 an hour on `c8g.xlarge`). The prices are constants in `deploy/cool/cool.py`; check them before quoting.
- **Per call:** the median time of each OpenCV call that the check uses.
- **Where the time goes:** the share of check time spent in each OpenCV call.

**Evidence that COOL executed the workload:** each result records `cv2.__file__`. For COOL that path is under `/opt/cool`, and the result has `"is_cool": true`. Each result also records the OpenCV build markers (KleidiCV, ARMPL, NEON, SVE), the CPU and the Python and numpy versions.

## What the profile predicts

A local run on the x86 development machine (pip OpenCV 5.0.0, 32 threads) shows where a Twice check spends its time:

| Share of check time | Call |
|---|---|
| 43% | `GaussianBlur` |
| 18% | `Keyframe.build`: resize, grey, CLAHE, SIFT (its resize and grey conversion also count in their own rows) |
| 5% | NanoDet on `cv2.dnn.ENGINE_NEW` |
| 1% or less each | `dilate`, `erode`, `imdecode`, `connectedComponentsWithStats`, `cvtColor`, `resize`, `warpPerspective` |
| the rest | numpy, FLANN matching, DIS optical flow and Python |

Most of the blur time is float32 blurs with large sigmas, for local normalisation and the illumination model. One such call at sigma 30 takes 123 ms on a 960 px image. So COOL can speed up Twice only to the extent that it speeds up float32 `GaussianBlur`, SIFT and the DNN engine. An independent COOL benchmark found blur and Canny faster on COOL, but `resize` and `warpAffine` slower ([cool-auto-tuner](https://github.com/DanKam0001/cool-auto-tuner)). Twice reports its own result either way.

## Run it

Before you start:

- You need AWS credentials.
- Install boto3 (`pip install boto3`).
- Accept the COOL Graviton4 subscription once in AWS Marketplace. It has a 7-day free trial.

```bash
python deploy/cool/cool.py bench     # about 30 to 45 minutes; well under $1 of instance time
python deploy/cool/cool.py serve     # the Twice app on COOL; prints http://<ip>/ and the terminate command
python deploy/cool/cool.py report    # rebuild docs/eval/cool/README.md from the saved JSON files
```

If the Marketplace search does not find the AMI, pass `--ami ami-...`. The serve mode stores photos on the instance and signs with a local key. The Lambda stack keeps S3, KMS and Bedrock.
