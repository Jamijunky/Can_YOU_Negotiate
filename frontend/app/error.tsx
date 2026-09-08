'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[ERROR BOUNDARY]", error.message, error.stack);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#f4f0e6] p-8">
      <div className="max-w-md text-center">
        <h2 className="text-4xl font-serif font-black text-[#1e1e1e] mb-4">
          Connection Error
        </h2>
        <p className="font-mono text-sm text-[#1e1e1e]/70 mb-2">
          Something went wrong with the negotiation link.
        </p>
        <p className="font-mono text-xs text-[#1e1e1e]/40 mb-6 break-all">
          {error.message || "Unknown error"}
        </p>
        <button
          onClick={() => {
            reset();
            window.location.href = "/";
          }}
          className="px-6 py-3 bg-[#1e1e1e] text-[#f4f0e6] font-mono font-bold uppercase tracking-widest border-2 border-[#1e1e1e] shadow-[4px_4px_0_0_#d99a4e] hover:translate-y-[2px] hover:shadow-[2px_2px_0_0_#d99a4e] transition-all"
        >
          Retry Connection
        </button>
      </div>
    </div>
  );
}
