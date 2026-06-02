type PushFlashMessageProps = {
  flash: { tone: "success" | "error" | "neutral"; message: string } | null;
};

/** 展示 Push Center 操作结果，供预览页和设置弹窗复用。 */
export function PushFlashMessage({ flash }: PushFlashMessageProps) {
  if (!flash) {
    return null;
  }
  return (
    <div
      className={[
        "rounded-2xl border px-4 py-3 text-sm",
        flash.tone === "success"
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : flash.tone === "error"
            ? "border-rose-200 bg-rose-50 text-rose-700"
            : "border-slate-200 bg-slate-50 text-slate-700",
      ].join(" ")}
    >
      {flash.message}
    </div>
  );
}
