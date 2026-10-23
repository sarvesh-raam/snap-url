import { Download, X } from "lucide-react";
import { QRCodeCanvas } from "qrcode.react";
import { useEffect, useRef } from "react";
import type { Link } from "../api";

export function QrDialog({ link, onClose }: { link: Link; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const canvasWrap = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.showModal();
  }, []);

  const download = () => {
    const canvas = canvasWrap.current?.querySelector("canvas");
    if (!canvas) return;
    const a = document.createElement("a");
    a.href = canvas.toDataURL("image/png");
    a.download = `snapurl-${link.code}.png`;
    a.click();
  };

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => e.target === ref.current && ref.current?.close()}
      className="m-auto w-[min(92vw,22rem)] rounded-2xl border border-line bg-card p-0 text-ink backdrop:bg-black/50"
    >
      <div className="p-5">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="font-semibold">QR code</h2>
            <p className="truncate font-mono text-xs text-ink-3">{link.short_url}</p>
          </div>
          <button className="icon-btn -mr-1 -mt-1" onClick={() => ref.current?.close()} aria-label="Close">
            <X size={17} />
          </button>
        </div>
        <div ref={canvasWrap} className="grid place-items-center rounded-xl bg-white p-4">
          <QRCodeCanvas
            value={link.short_url}
            size={480}
            level="M"
            marginSize={1}
            style={{ width: "100%", maxWidth: 240, height: "auto" }}
          />
        </div>
        <button className="btn btn-primary mt-4 w-full" onClick={download}>
          <Download size={16} /> Download PNG
        </button>
      </div>
    </dialog>
  );
}
