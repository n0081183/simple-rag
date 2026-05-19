"use client";

import { Fragment, useMemo, useState } from "react";
import { cn } from "@/lib/utils";

export type Verdict = "MET" | "PARTIAL" | "NOT_MET" | "UNCLEAR";

export interface VerificationRow {
  requirement_id: string;
  requirement_text: string;
  verdict: Verdict;
  confidence: string;
  evidence: { source_file: string; topic_url: string; quote: string }[];
  reasoning_steps: string[];
  caveats?: string | null;
}

const VERDICT_STYLE: Record<Verdict, string> = {
  MET: "text-emerald-600 dark:text-emerald-400",
  PARTIAL: "text-amber-600 dark:text-amber-400",
  NOT_MET: "text-red-600 dark:text-red-400",
  UNCLEAR: "text-muted-foreground",
};

export function ResultsTable({ rows }: { rows: VerificationRow[] }) {
  const [filter, setFilter] = useState<string>("all");
  const [q, setQ] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return rows.filter((r) => {
      if (filter !== "all" && r.verdict !== filter) return false;
      if (q && !r.requirement_text.toLowerCase().includes(q.toLowerCase())) return false;
      return true;
    });
  }, [rows, filter, q]);

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <div className="flex flex-wrap gap-2 border-b border-border bg-muted/40 px-4 py-3">
        <input
          type="search"
          placeholder="Filter requirements…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm flex-1 min-w-[200px]"
        />
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm"
        >
          <option value="all">All verdicts</option>
          <option value="MET">MET</option>
          <option value="PARTIAL">PARTIAL</option>
          <option value="NOT_MET">NOT_MET</option>
          <option value="UNCLEAR">UNCLEAR</option>
        </select>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/30 sticky top-0">
            <tr className="text-left text-muted-foreground">
              <th className="px-4 py-2 font-medium">Verdict</th>
              <th className="px-4 py-2 font-medium">Confidence</th>
              <th className="px-4 py-2 font-medium">Requirement</th>
              <th className="px-4 py-2 font-medium w-20">Evidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filtered.map((r) => (
              <Fragment key={r.requirement_id}>
                <tr
                  className="hover:bg-muted/20 cursor-pointer"
                  onClick={() =>
                    setExpanded(expanded === r.requirement_id ? null : r.requirement_id)
                  }
                >
                  <td className={cn("px-4 py-2 font-mono font-medium", VERDICT_STYLE[r.verdict])}>
                    {r.verdict}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs">{r.confidence}</td>
                  <td className="px-4 py-2 max-w-md truncate">{r.requirement_text}</td>
                  <td className="px-4 py-2 text-center">{r.evidence.length}</td>
                </tr>
                {expanded === r.requirement_id && (
                  <tr>
                    <td colSpan={4} className="px-4 py-3 bg-muted/10 text-xs space-y-2">
                      <p className="whitespace-pre-wrap">{r.requirement_text}</p>
                      {r.reasoning_steps.map((s, i) => (
                        <p key={i}>• {s}</p>
                      ))}
                      {r.evidence.map((e, i) => (
                        <p key={i} className="font-mono">
                          <a href={e.topic_url} className="underline" target="_blank" rel="noreferrer">
                            {e.source_file}
                          </a>
                          : {e.quote.slice(0, 200)}…
                        </p>
                      ))}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
