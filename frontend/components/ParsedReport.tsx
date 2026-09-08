"use client";

import ReactMarkdown from "react-markdown";
import { memo } from "react";

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

// Letter grade → stamp color + label
function gradeStamp(letter: string): { bg: string; border: string; text: string; label: string } {
  const l = letter.charAt(0).toUpperCase();
  if (l === "A") return { bg: "rgba(39,174,96,0.08)",  border: "#27ae60", text: "#27ae60",  label: "EXCELLENT" };
  if (l === "B") return { bg: "rgba(200,137,62,0.08)", border: "#c8893e", text: "#c8893e",  label: "ADEQUATE" };
  if (l === "C") return { bg: "rgba(200,137,62,0.06)", border: "rgba(200,137,62,0.5)", text: "rgba(200,137,62,0.7)", label: "MARGINAL" };
  if (l === "D") return { bg: "rgba(192,57,43,0.08)", border: "#c0392b", text: "#c0392b", label: "POOR" };
  return { bg: "rgba(192,57,43,0.12)", border: "#c0392b", text: "#c0392b", label: "FAILED" };
}

const ParsedReport = memo(function ParsedReport({ text }: { text: string }) {
  const sections = extractSections(text);

  const gradingSection    = sections.find((s) => s.title.includes("Grading Summary"));
  const adviceSection     = sections.find((s) => s.title.includes("Advice"));
  const keyMomentsSection = sections.find((s) => s.title.includes("Key Moments"));
  const profileSection    = sections.find((s) => s.title.includes("Subject Profile"));

  const gradeItems = (gradingSection?.content.split("\n") ?? [])
    .map((line) => {
      const match = line.match(GRADE_REGEX);
      return match ? { category: match[1].replace(/\*/g, "").trim(), grade: match[2].trim() } : null;
    })
    .filter(Boolean) as { category: string; grade: string }[];

  // Fallback: raw markdown
  if (gradeItems.length === 0 && !adviceSection) {
    return (
      <div className="font-mono text-xs text-white/50 leading-relaxed prose-invert">
        <ReactMarkdown>{text}</ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      {/* ── Grading grid ── */}
      {gradeItems.length > 0 && (
        <div>
          <div className="font-mono text-[9px] tracking-[0.2em] text-white/20 uppercase mb-3">
            Performance Assessment
          </div>
          <div className="space-y-0" role="list" aria-label="Grading summary">
            {gradeItems.map((item, i) => {
              const stamp = gradeStamp(item.grade);
              return (
                <div
                  key={i}
                  role="listitem"
                  className="flex items-center justify-between py-2.5 border-b border-white/6 last:border-0"
                >
                  <span className="font-mono text-[11px] text-white/50 uppercase tracking-wider">
                    {item.category}
                  </span>
                  <div className="flex items-center gap-3">
                    <span
                      className="font-mono text-[9px] tracking-[0.15em] uppercase"
                      style={{ color: stamp.text, opacity: 0.6 }}
                    >
                      {stamp.label}
                    </span>
                    {/* Stamped grade */}
                    <span
                      className="font-mono text-sm font-black px-2 py-0.5 border"
                      style={{
                        color: stamp.text,
                        borderColor: stamp.border,
                        backgroundColor: stamp.bg,
                        transform: `rotate(${(i % 3) - 1}deg)`,
                        display: "inline-block",
                      }}
                      aria-label={`${item.category}: ${item.grade}`}
                    >
                      {item.grade}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Key Moments ── */}
      {keyMomentsSection && (
        <div>
          <div className="font-mono text-[9px] tracking-[0.2em] text-white/20 uppercase mb-2">
            Key Moments
          </div>
          <div className="border-l border-white/10 pl-4 font-mono text-[11px] text-white/40 leading-relaxed space-y-1 [&_strong]:text-white/60 [&_strong]:font-bold [&_li]:list-none [&_li]:pl-0 [&_li::before]:content-['—_'] [&_li::before]:opacity-40">
            <ReactMarkdown>{keyMomentsSection.content}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* ── Subject Profile ── */}
      {profileSection && (
        <div>
          <div className="font-mono text-[9px] tracking-[0.2em] text-white/20 uppercase mb-2">
            Subject Profile
          </div>
          <div className="font-mono text-[11px] text-white/35 leading-relaxed [&_strong]:text-white/55 [&_strong]:font-bold">
            <ReactMarkdown>{profileSection.content}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* ── Actionable Advice ── */}
      {adviceSection && (
        <div>
          <div className="font-mono text-[9px] tracking-[0.2em] text-[#c0392b]/50 uppercase mb-2">
            Recommendations
          </div>
          <div className="border-l-2 border-[#c0392b]/20 pl-4 font-mono text-[11px] text-white/40 leading-relaxed space-y-1 [&_strong]:text-white/60 [&_strong]:font-bold">
            <ReactMarkdown>{adviceSection.content}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
});

export default ParsedReport;
