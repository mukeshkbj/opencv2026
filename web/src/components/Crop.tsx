type Box = [number, number, number, number];

export interface View {
  before: string;
  after: string;
  w: number;
  h: number;
}

function area(box: Box, w: number, h: number): Box {
  const side = Math.min(Math.max(box[2], box[3], 48) * 2.2, w, h);
  const x = Math.min(Math.max(box[0] + box[2] / 2 - side / 2, 0), w - side);
  const y = Math.min(Math.max(box[1] + box[3] / 2 - side / 2, 0), h - side);
  return [x, y, side, side];
}

function Crop({ src, box, view, label }: { src: string; box: Box; view: View; label: string }) {
  const [x, y, s] = area(box, view.w, view.h);
  return (
    <figure className="crop">
      <div className="crop-frame">
        <img
          src={src}
          alt=""
          draggable={false}
          style={{ width: `${(view.w / s) * 100}%`, left: `${(-x / s) * 100}%`, top: `${(-y / s) * 100}%` }}
        />
        <span
          className="crop-box"
          style={{ left: `${((box[0] - x) / s) * 100}%`, top: `${((box[1] - y) / s) * 100}%`, width: `${(box[2] / s) * 100}%`, height: `${(box[3] / s) * 100}%` }}
        />
      </div>
      <figcaption className="label">{label}</figcaption>
    </figure>
  );
}

export default function CropPair({ box, view }: { box: Box; view: View }) {
  return (
    <div className="crop-pair">
      <Crop src={view.before} box={box} view={view} label="Move-in" />
      <Crop src={view.after} box={box} view={view} label="Move-out" />
    </div>
  );
}
