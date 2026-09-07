"use client";

import ReactMarkdown from "react-markdown";
import { memo } from "react";

const SUMMARY_REGEX = /\*\*Grading Summary\*\*([\s\S]*?)(?=\*\*Advice\*\*|$)/;
const ADVICE_REGEX = /\*\*Advice\*\*([\s\S]*)/;
const GRADE_REGEX = /\*\*(.*?):\*\*\s*(.*)/;

const ParsedReport = memo(function ParsedReport({ text }: { text: string }) {
  const summaryMatch = text.match(SUMMARY_REGEX);
  const adviceMatch = text.match(ADVICE_REGEX);

  const summaryLines = summaryMatch ? summaryMatch[1].trim().split("\n") : [];
  const adviceText = adviceMatch ? adviceMatch[1].trim() : text;

  if (summaryLines.length === 0 && adviceText === text) {
    return (
      <div className="font-serif prose prose-sm text-[#1e1e1e]">
        <ReactMarkdown>{text}</ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col gap-6">
      <div
        className="grid grid-cols-1 gap-4 bg-white/40 p-6 border-2 border-[#1e1e1e] shadow-[4px_4px_0_0_#1e1e1e]"
        role="list"
        aria-label="Grading summary"
      >
        {summaryLines.map((line, i) => {
          const match = line.match(GRADE_REGEX);
          if (match) {
            const cat = match[1].replace(/\*/g, "").trim();
            const grade = match[2].trim();
            const isGood = grade.includes("A") || grade.includes("B");
            const isMid = grade.includes("C");
            return (
              <div
                key={i}
                role="listitem"
                className="flex justify-between items-center border-b-2 border-[#1e1e1e]/10 pb-3 last:border-0 last:pb-0"
              >
                <span className="font-serif font-bold text-lg text-[#1e1e1e] uppercase tracking-wide">
                  {cat}
                </span>
                <span
                  className={`font-mono font-black text-2xl px-4 py-1 border-2 border-[#1e1e1e] shadow-[2px_2px_0_0_#1e1e1e] ${
                    isGood
                      ? "bg-[#4ade80]"
                      : isMid
                        ? "bg-[#facc15]"
                        : "bg-[#dc2626] text-white"
                  }`}
                  aria-label={`${cat}: ${grade}`}
                >
                  {grade}
                </span>
              </div>
            );
          }
          return null;
        })}
      </div>

      <div className="bg-white/80 p-6 border-l-8 border-[#1e1e1e] shadow-[4px_4px_0_0_#1e1e1e]">
        <h4 className="font-mono uppercase tracking-widest text-sm font-black mb-3 text-[#dc2626]">
          Actionable Advice
        </h4>
        <div className="font-serif text-[#1e1e1e]/90 leading-relaxed">
          <ReactMarkdown>{adviceText}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
});

export default ParsedReport;
