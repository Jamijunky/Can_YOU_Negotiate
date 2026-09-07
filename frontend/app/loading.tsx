export default function Loading() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#f4f0e6]">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-[#1e1e1e] border-t-transparent rounded-full animate-spin" />
        <p className="font-mono text-sm text-[#1e1e1e] tracking-widest uppercase animate-pulse">
          Establishing secure channel...
        </p>
      </div>
    </div>
  );
}
