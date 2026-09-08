"use client";

import ReactMarkdown from "react-markdown";
import { memo } from "react";

const SECTION_REGEX = /\*\*(.*?)\*\*\n([\s\S]*?)(?=\*\*[A-Z]|\n*$)/g;
const GRADE_REGEX = /\*\*(.*?):\*\*\s*(.*)/;

function extractSections(text: string): { title: string; content: string }[] {
  const sections: { title: string; content: string }[] = [];
  let match;
  const regex = /\*\*(.*?)\*\*\n([\s\S]*?)(?=\*\*[A-Z]|\n*$)/g;
  while ((match = regex.exec(text)) !== null) {
    sections.push({ title: match[1].trim(), content: match[2].trim() });
  }
  return sections;
}

const ParsedReport = memo(function ParsedReport({ text }: { text: string }) {
  const sections = extractSections(text);

  // Find specific sections
  const gradingSection = sections.find((s) => s.title.includes("Grading Summary"));
  const adviceSection = sections.find((s) => s.title.includes("Advice"));
  const keyMomentsSection = sections.find((s) => s.title.includes("Key Moments"));
  const subjectProfileSection = sections.find((s) => s.title.includes("Subject Profile"));

  const gradingLines = gradingSection ? gradingSection.content.split("\n") : [];
  const gradeItems = gradingLines
    .map((line) => {
      const match = line.match(GRADE_REGEX);
      if (match) {
        return {
          category: match[1].replace(/\*/g, "").trim(),
          grade: match[2].trim(),
        };
      }
      return null;
    })
    .filter(Boolean) as { category: string; grade: string }[];

  if (gradeItems.length === 0 && !adviceSection) {
    return (
      <div className="font-serif prose prose-sm text-[#1e1e1e]">
        <ReactMarkdown>{text}</ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Grading Grid */}
      {gradeItems.length > 0 && (
        <div
          className="grid grid-cols-1 gap-4 bg-white/40 p-6 border-2 border-[#1e1e1e] shadow-[4px_4px_0_0_#1e1e1e]"
          role="list"
          aria-label="Grading summary"
        >
          {gradeItems.map((item, i) => {
            const letter = item.grade.charAt(0).toUpperCase();
            const isGood = letter === "A" || letter === "B";
            const isMid = letter === "C";
            return (
              <div
                key={i}
                role="listitem"
                className="flex justify-between items-center border-b-2 border-[#1e1e1e]/10 pb-3 last:border-0 last:pb-0"
              >
                <span className="font-serif font-bold text-lg text-[#1e1e1e] uppercase tracking-wide">
                  {item.category}
                </span>
                <span
                  className={`font-mono font-black text-2xl px-4 py-1 border-2 border-[#1e1e1e] shadow-[2px_2px_0_0_#1e1e1e] ${
                    isGood
                      ? "bg-[#4ade80]"
                      : isMid
                        ? "bg-[#facc15]"
                        : "bg-[#dc2626] text-white"
                  }`}
                  aria-label={`${item.category}: ${item.grade}`}
                >
                  {item.grade}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Key Moments */}
      {keyMomentsSection && (
        <div className="bg-[#1e1e1e] text-[#f4f0e6] p-6 border-2 border-[#d99a4e] shadow-[4px_4px_0_0_#d99a4e]">
          <h4 className="font-mono uppercase tracking-widest text-sm font-black mb-3 text-[#d99a4e]">
            Key Moments
          </h4>
          <div className="font-serif text-sm leading-relaxed space-y-2">
            <ReactMarkdown>{keyMomentsSection.content}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Subject Profile */}
      {subjectProfileSection && (
        <div className="bg-white/60 p-6 border-l-8 border-[#d99a4e] shadow-[4px_4px_0_0_#1e1e1e]">
          <h4 className="font-mono uppercase tracking-widest text-sm font-black mb-3 text-[#1e1e1e]">
            Subject Profile
          </h4>
          <div className="font-serif text-[#1e1e1e]/90 leading-relaxed">
            <ReactMarkdown>{subjectProfileSection.content}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Advice */}
      {adviceSection && (
        <div className="bg-white/80 p-6 border-l-8 border-[#1e1e1e] shadow-[4px_4px_0_0_#1e1e1e]">
          <h4 className="font-mono uppercase tracking-widest text-sm font-black mb-3 text-[#dc2626]">
            Actionable Advice
          </h4>
          <div className="font-serif text-[#1e1e1e]/90 leading-relaxed">
            <ReactMarkdown>{adviceSection.content}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
});

export default ParsedReport;
