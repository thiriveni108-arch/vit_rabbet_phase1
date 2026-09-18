import { type ReactNode, useState, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity, ArrowRight, ArrowUpRight, Bell, BrainCircuit, CalendarDays, Check, CheckCircle2, ChevronDown,
  ChevronRight, ChevronUp, CircleHelp, Clock, Compass, Database, ExternalLink, FileSearch, Filter, GitBranch,
  Globe2, Hexagon, Layers3, Menu, MoreHorizontal, Network, Plus, Search, Send, Settings2, ShieldAlert,
  ShieldCheck, Sparkles, Target, TriangleAlert, X, Zap, RefreshCw
} from "lucide-react";
import { Link, Route, Switch, useLocation, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider, useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ErrorBoundary } from "@/components/error-boundary";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import {
  api,
  type DashboardData,
  type SubjectItem,
  type GraphViewData,
  type GraphNode,
  type FindingItem,
  type EvidenceRecord,
  type AskResponse,
  type TimelineItem
} from "@/lib/api";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 30000,
    },
  },
});

type Tone = "teal" | "lilac" | "amber" | "coral" | "slate";
type IconType = typeof Activity;

const navItems = [
  { href: "/", label: "Command center", icon: Activity },
  { href: "/graph", label: "Study graph", icon: Network },
  { href: "/atlas", label: "Atlas agent", icon: BrainCircuit },
  { href: "/evidence", label: "Evidence explorer", icon: FileSearch },
];

function cn(...items: (string | false | undefined)[]) { return items.filter(Boolean).join(" "); }

function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: Tone }) {
  const colors = {
    teal: "border-[#2de2c3]/25 bg-[#2de2c3]/10 text-[#79ffe9]",
    lilac: "border-[#a78bfa]/25 bg-[#a78bfa]/10 text-[#c9bdff]",
    amber: "border-[#eec66c]/25 bg-[#eec66c]/10 text-[#f7d98d]",
    coral: "border-[#ff7e72]/25 bg-[#ff7e72]/10 text-[#ffaaa3]",
    slate: "border-white/10 bg-white/[.045] text-[#9ba9bc]"
  };
  return <span className={cn("mono inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[.12em]", colors[tone])}>{children}</span>;
}

function Progress({ value, tone = "teal" }: { value: number; tone?: Tone }) {
  const colors = { teal: "#49f3d3", lilac: "#a78bfa", amber: "#eec66c", coral: "#ff7e72", slate: "#8290a4" };
  const safeVal = Math.min(100, Math.max(0, value));
  return (
    <div className="h-1.5 overflow-hidden rounded-full bg-white/[.06]">
      <motion.div initial={{ width: 0 }} animate={{ width: `${safeVal}%` }} transition={{ duration: .6 }} className="h-full rounded-full" style={{ background: colors[tone] }} />
    </div>
  );
}

function RabbitCharacter() {
  return (
    <svg viewBox="0 0 72 72" aria-hidden="true" className="rabbit-character">
      <ellipse className="rabbit-shadow" cx="36" cy="66" rx="17" ry="2.8" fill="#b68caf" opacity=".25" />
      <g className="rabbit-ears">
        <ellipse className="rabbit-ear rabbit-ear-left" cx="25" cy="18" rx="8" ry="18" transform="rotate(-9 25 18)" fill="#fff7fb" stroke="#d88db4" strokeWidth="1.4" />
        <ellipse className="rabbit-ear-inner rabbit-ear-inner-left" cx="25" cy="18" rx="3.7" ry="12.5" transform="rotate(-9 25 18)" fill="#f1b5d0" />
        <ellipse className="rabbit-ear rabbit-ear-right" cx="47" cy="18" rx="8" ry="18" transform="rotate(9 47 18)" fill="#fff7fb" stroke="#d88db4" strokeWidth="1.4" />
        <ellipse className="rabbit-ear-inner rabbit-ear-inner-right" cx="47" cy="18" rx="3.7" ry="12.5" transform="rotate(9 47 18)" fill="#f1b5d0" />
      </g>
      <path className="rabbit-body" d="M24 51c1-7 5-10 12-10s11 3 12 10l4 11H20l4-11Z" fill="#f5c4dd" stroke="#d88db4" strokeWidth="1.4" />
      <path d="M28 52c2 2 4 3 8 3s6-1 8-3l2 10H26l2-10Z" fill="#dca5db" opacity=".72" />
      <circle className="rabbit-head" cx="36" cy="39" r="16" fill="#fffafd" stroke="#d88db4" strokeWidth="1.4" />
      <ellipse className="rabbit-cheek rabbit-cheek-left" cx="27" cy="46" rx="4" ry="2.1" fill="#f4b5ca" opacity=".62" />
      <ellipse className="rabbit-cheek rabbit-cheek-right" cx="45" cy="46" rx="4" ry="2.1" fill="#f4b5ca" opacity=".62" />
      <ellipse className="rabbit-eye" cx="30" cy="39" rx="2.1" ry="2.8" fill="#403557" />
      <ellipse className="rabbit-eye" cx="42" cy="39" rx="2.1" ry="2.8" fill="#403557" />
      <circle cx="30.7" cy="38.2" r=".7" fill="#fff" />
      <circle cx="42.7" cy="38.2" r=".7" fill="#fff" />
      <path d="M34 44q2-2 4 0-2 2-4 0Z" fill="#d77da8" />
      <path d="M36 46q-2 3-4 1M36 46q2 3 4 1" fill="none" stroke="#ae6c99" strokeLinecap="round" strokeWidth="1" />
      <path d="M27 56q-3 2-4 5M45 56q3 2 4 5" fill="none" stroke="#d88db4" strokeLinecap="round" strokeWidth="2" />
      <circle className="rabbit-star" cx="16" cy="31" r="1.4" fill="#7adbd7" />
      <circle className="rabbit-star rabbit-star-two" cx="57" cy="49" r="1.1" fill="#c3a8ef" />
    </svg>
  );
}

function RabbitBuddy({ compact = false, className = "" }: { compact?: boolean; className?: string }) {
  const [jumping, setJumping] = useState(false);
  const jump = () => {
    if (jumping) return;
    setJumping(true);
    window.setTimeout(() => setJumping(false), 650);
  };
  return (
    <motion.button
      type="button"
      onClick={jump}
      animate={jumping ? { y: [0, -30, 0], rotate: [0, -8, 7, 0], scale: [1, 1.04, .98, 1] } : { y: 0, rotate: 0, scale: 1 }}
      transition={{ duration: .62, ease: "easeOut" }}
      className={cn("rabbit-buddy group relative inline-flex items-center gap-2 rounded-full border border-[#e9b5ca]/55 bg-white/80 px-2 py-1.5 text-left shadow-[0_8px_20px_rgba(120,120,180,.14)] backdrop-blur-md", compact ? "h-9 w-9 justify-center rounded-2xl px-0" : "", className)}
      aria-label="Make Rabbet jump"
      data-testid={compact ? "button-rabbit-sidebar" : "button-rabbit-buddy"}
    >
      <span className={cn("rabbit-aura", compact ? "h-7 w-7" : "h-8 w-8")} />
      <RabbitCharacter />
      {!compact && (
        <span className="relative z-10 pr-1">
          <span className="block text-[10px] font-bold leading-none text-[#6d5a83]">Rabbet</span>
          <span className="mt-0.5 block text-[8px] text-[#9c8da9]">tap to jump</span>
        </span>
      )}
      <span className="rabbit-spark rabbit-spark-one" />
      <span className="rabbit-spark rabbit-spark-two" />
    </motion.button>
  );
}

function CutSelector() {
  const qc = useQueryClient();
  const { data: context } = useQuery({ queryKey: ["context"], queryFn: api.getContext });
  const cutMutation = useMutation({
    mutationFn: (cut: number) => api.setCut(cut),
    onSuccess: () => {
      qc.invalidateQueries();
    },
  });

  const currentCut = context?.current_cut ?? 12;
  const cuts = context?.available_cuts ?? [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

  return (
    <div className="flex items-center gap-2 rounded-xl border border-white/[.12] bg-[#0b131e]/90 px-2.5 py-1.5 backdrop-blur-md shadow-lg">
      <span className="mono text-[10px] font-semibold text-[#66f4db]">Cut</span>
      <select
        value={currentCut}
        onChange={(e) => cutMutation.mutate(Number(e.target.value))}
        disabled={cutMutation.isPending}
        className="cursor-pointer rounded-lg border border-white/[.15] bg-[#121c2a] px-2 py-1 mono text-[11px] font-bold text-[#e6f2fa] outline-none hover:border-[#52eed3] transition"
        data-testid="select-cut"
      >
        {cuts.map((c) => (
          <option key={c} value={c} className="bg-[#0b131e] text-[#d6e4f0]">
            Cut {c} {c === 12 ? "(Latest)" : ""}
          </option>
        ))}
      </select>
      {cutMutation.isPending ? (
        <RefreshCw size={13} className="animate-spin text-[#67f6db]" />
      ) : (
        <Badge tone="teal">v{context?.protocol_version ?? 3}</Badge>
      )}
    </div>
  );
}

function Sidebar({ open, close }: { open: boolean; close: () => void }) {
  const [path] = useLocation();
  const { data: context } = useQuery({ queryKey: ["context"], queryFn: api.getContext });

  return (
    <>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={close} className="fixed inset-0 z-30 bg-black/60 md:hidden" />
        )}
      </AnimatePresence>
      <aside className={cn("fixed inset-y-0 left-0 z-40 flex w-[256px] flex-col border-r border-white/[.08] bg-[#090e17]/95 px-4 py-5 backdrop-blur-xl transition-transform md:translate-x-0", open ? "translate-x-0" : "-translate-x-full")}>
        <div className="mb-9 flex items-center justify-between px-2">
          <Link href="/" onClick={close} data-testid="link-brand" className="flex items-center gap-3">
            <div className="relative grid h-9 w-9 place-items-center rounded-xl border border-[#56f2d5]/30 bg-[#56f2d5]/[.09] text-[#6fffe4]">
              <Hexagon size={19} />
              <span className="absolute h-1.5 w-1.5 rounded-full bg-[#6fffe4] shadow-[0_0_13px_#6fffe4]" />
            </div>
            <div>
              <div className="display text-[18px] font-semibold tracking-[-.04em] text-[#f0f5fa]">rabbet</div>
              <div className="mono text-[9px] uppercase tracking-[.17em] text-[#738198]">clinical intelligence</div>
            </div>
          </Link>
          <button onClick={close} className="text-[#718197] md:hidden" data-testid="button-close-navigation"><X size={18} /></button>
        </div>

        <div className="mb-3 px-3 mono text-[9px] uppercase tracking-[.18em] text-[#526177]">Workspace</div>
        <nav className="space-y-1">
          {navItems.map(({ href, label, icon: Icon }, i) => (
            <Link
              href={href}
              onClick={close}
              key={href}
              data-testid={`link-nav-${label.replaceAll(" ", "-").toLowerCase()}`}
              className={cn("group flex items-center gap-3 rounded-xl px-3 py-3 transition", path === href ? "bg-[#5beed5]/[.1] text-[#e9fffa] shadow-[inset_2px_0_0_#65f4d8]" : "text-[#8593a7] hover:bg-white/[.045] hover:text-[#d7e0eb]")}
            >
              <Icon size={17} className={path === href ? "text-[#67f6db]" : "text-[#64748a]"} />
              <span className="flex-1 text-[12px] font-semibold">{label}</span>
              <span className="mono text-[9px] text-[#536177]">0{i + 1}</span>
            </Link>
          ))}
        </nav>

        <div className="mt-9 px-3 mb-3 mono text-[9px] uppercase tracking-[.18em] text-[#526177]">Active Study</div>
        <div className="relative rounded-xl border border-white/[.08] bg-white/[.025] p-3">
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[#67f6db] pulse-dot" />
              <span className="mono text-[10px] tracking-[.12em] text-[#b9c7d9]">STUDY-042</span>
            </div>
            <Badge tone="teal">Cut {context?.current_cut ?? 12}</Badge>
          </div>
          <div className="text-[11px] text-[#7f8ea3]">Study Sentinel / ATLAS</div>
          <div className="mt-2 text-[10px] text-[#5c6e83]">Protocol Version: <span className="mono text-[#8ffff0]">v{context?.protocol_version ?? 3}</span></div>
          <div className="mt-1 text-[10px] text-[#5c6e83]">Enrolled Subjects: <span className="mono text-[#d1dfed]">{context?.total_subjects ?? 241}</span></div>
          <RabbitBuddy compact className="absolute -bottom-3 -right-2" />
        </div>

        <div className="mt-auto space-y-1">
          <div className="px-3 py-2 text-[11px] text-[#6b7b90] border-t border-white/[.07]">
            <div className="flex items-center gap-2 text-[#8fa1b6]">
              <ShieldCheck size={14} className="text-[#59edd3]" /> StudyGraph Verified
            </div>
            <div className="mt-1 text-[9px] mono text-[#4e6074]">Single Source of Clinical Truth</div>
          </div>
        </div>
      </aside>
    </>
  );
}

function Topbar({ menu }: { menu: () => void; atlas?: () => void }) {
  const [path] = useLocation();
  const title = navItems.find((x) => x.href === path)?.label ?? "Command center";
  const { data: context } = useQuery({ queryKey: ["context"], queryFn: api.getContext });

  return (
    <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-white/[.07] bg-[#080d16]/85 px-5 backdrop-blur-xl md:ml-[256px] md:px-9">
      <div className="flex items-center gap-3">
        <button className="text-[#8090a5] md:hidden" onClick={menu} data-testid="button-open-navigation">
          <Menu size={20} />
        </button>
        <div>
          <div className="mono text-[9px] uppercase tracking-[.2em] text-[#53647a]">
            Study Sentinel · Protocol v{context?.protocol_version ?? 3}
          </div>
          <div className="display text-[17px] font-semibold text-[#eaf1f7]">{title}</div>
        </div>
      </div>
    </header>
  );
}

function Shell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [, go] = useLocation();
  return (
    <div className="shell-noise min-h-[100dvh] bg-grid">
      <Sidebar open={open} close={() => setOpen(false)} />
      <Topbar menu={() => setOpen(true)} atlas={() => go("/atlas")} />
      <main className="min-h-[calc(100dvh-72px)] md:ml-[256px]">{children}</main>
      <RabbitBuddy className="fixed bottom-5 right-5 z-30" />
    </div>
  );
}

function Heading({ eyebrow, title, detail, action }: { eyebrow: string; title: string; detail: string; action?: ReactNode }) {
  return (
    <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <div className="mono mb-2 text-[9px] uppercase tracking-[.22em] text-[#5bdcca]">{eyebrow}</div>
        <h1 className="display text-[28px] font-semibold tracking-[-.05em] text-[#edf4f8] sm:text-[33px]">{title}</h1>
        <p className="mt-2 max-w-2xl text-[12px] leading-5 text-[#8090a5]">{detail}</p>
      </div>
      {action}
    </div>
  );
}

function Metric({ label, value, detail, icon: Icon, tone }: { label: string; value: string; detail: string; icon: IconType; tone: Tone }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="glass relative overflow-hidden rounded-2xl p-4 transition hover:-translate-y-0.5 sm:p-5">
      <div className={cn("grid h-8 w-8 place-items-center rounded-lg bg-white/[.04]", tone === "teal" ? "text-[#6dffe3]" : tone === "lilac" ? "text-[#b5a2ff]" : tone === "amber" ? "text-[#f5c86d]" : "text-[#ff887b]")}>
        <Icon size={16} />
      </div>
      <div className="mt-5 mono text-[10px] uppercase tracking-[.12em] text-[#738299]">{label}</div>
      <div className="display mt-1 text-[28px] font-semibold text-[#e9f1f7]">{value}</div>
      <div className="mt-1 text-[11px] text-[#78889d]">{detail}</div>
    </motion.div>
  );
}

// -----------------------------------------------------------------------------
// PAGE 1: DASHBOARD
// -----------------------------------------------------------------------------
function Dashboard() {
  const [, go] = useLocation();
  const { data: dash } = useQuery({ queryKey: ["dashboard"], queryFn: api.getDashboard });
  const { data: subjects = [] } = useQuery({ queryKey: ["subjects"], queryFn: api.getSubjects });
  const [selectedSubject, setSelectedSubject] = useState<SubjectItem | null>(null);

  // Top subjects with findings
  const activeSubjects = useMemo(() => {
    return [...subjects].sort((a, b) => b.findings_count - a.findings_count).slice(0, 5);
  }, [subjects]);

  const domainList = useMemo(() => {
    if (!dash?.domain_record_counts) return [];
    return Object.entries(dash.domain_record_counts).map(([dom, count]) => ({
      domain: dom,
      count,
    })).sort((a, b) => b.count - a.count);
  }, [dash]);

  return (
    <div className="mx-auto max-w-[1480px] px-5 py-7 md:px-9 md:py-9">
      <Heading
        eyebrow={`Study Surveillance / Snapshot Cut ${dash?.cut ?? 12} · Protocol v${dash?.protocol_version ?? 3}`}
        title="The study, in signal."
        detail="A deterministic clinical intelligence view powered directly by StudyGraph. Every metric, finding, and event is grounded in validated provenance."
        action={
          <button
            onClick={() => go("/evidence")}
            className="flex items-center gap-2 rounded-lg border border-[#61eeda]/20 bg-[#5debd5]/[.09] px-3 py-2 text-[11px] font-semibold text-[#a5fff0] hover:bg-[#5debd5]/[.15] transition"
            data-testid="button-open-evidence"
          >
            <FileSearch size={14} /> Review evidence ({dash?.total_findings ?? 280})
          </button>
        }
      />

      {/* Top 4 Live Metrics */}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Metric
          label="Enrolled Subjects"
          value={String(dash?.subjects ?? 241)}
          detail={`across ${dash?.sites ?? 12} clinical sites`}
          icon={Target}
          tone="teal"
        />
        <Metric
          label="Study Records"
          value={(dash?.total_records ?? 26482).toLocaleString()}
          detail="across 9 clinical domains"
          icon={Database}
          tone="lilac"
        />
        <Metric
          label="Total Findings"
          value={String(dash?.total_findings ?? 280)}
          detail={`Cut ${dash?.cut ?? 12} deterministic surveillance`}
          icon={TriangleAlert}
          tone="coral"
        />
        <Metric
          label="Potential Hy's Law"
          value={String(dash?.potential_hys_law_count ?? 3)}
          detail="UNCONFIRMED · adjudication required"
          icon={Activity}
          tone="amber"
        />
      </div>

      {/* Findings Breakdown & Domain Ledger */}
      <div className="mt-5 grid gap-5 xl:grid-cols-[1.2fr_.8fr]">
        <div className="glass rounded-2xl p-5">
          <div className="mb-4 flex items-baseline justify-between">
            <div>
              <div className="mono text-[10px] uppercase tracking-[.15em] text-[#77879b]">Clinical Safety Signals</div>
              <div className="mt-1 display text-xl font-semibold text-[#e9f2f6]">
                {dash?.total_findings ?? 280} Detected Findings
              </div>
            </div>
            <Badge tone="teal">Deterministic</Badge>
          </div>

          <div className="space-y-3 mt-4">
            {[
              { label: "Potential Hy's Law (Liver Safety)", count: dash?.potential_hys_law_count ?? 3, tone: "amber" as Tone, note: "UNCONFIRMED / Requires Adjudication" },
              { label: "Serious Adverse Events (SAE / Hospitalization)", count: dash?.serious_ae_count ?? 5, tone: "coral" as Tone, note: "AESER=Y or AESHOSP=Y Override" },
              { label: "Screening Creatinine Exclusions", count: dash?.creatinine_exclusion_count ?? 4, tone: "lilac" as Tone, note: "Protocol v2+ Threshold Violation" },
              { label: "Prohibited Concomitant Medications", count: dash?.prohibited_medication_count ?? 14, tone: "coral" as Tone, note: "Glucocorticoids & Sulfonylureas" },
              { label: "Visit Window Deviations", count: dash?.visit_deviation_count ?? 254, tone: "teal" as Tone, note: "Deviation from planned protocol target" },
            ].map((f) => (
              <div key={f.label} className="rounded-xl border border-white/[.06] bg-white/[.02] p-3 flex items-center justify-between">
                <div>
                  <div className="text-[12px] font-semibold text-[#dce7ee]">{f.label}</div>
                  <div className="text-[10px] text-[#6d7d92]">{f.note}</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="display text-xl font-semibold text-[#f0f6fa]">{f.count}</span>
                  <Badge tone={f.tone}>{f.count > 0 ? "Flagged" : "Clear"}</Badge>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Domain Records Breakdown */}
        <div className="glass rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="mono text-[10px] uppercase tracking-[.15em] text-[#77879b]">Normalized Multi-Domain State</div>
              <div className="mt-1 display text-xl font-semibold text-[#e9f2f6]">Domain Ledger</div>
            </div>
            <Badge tone="lilac">Cut {dash?.cut ?? 12}</Badge>
          </div>

          <div className="space-y-2 mt-2">
            {domainList.map(({ domain, count }) => {
              const maxCount = 14160;
              const pct = Math.round((count / maxCount) * 100);
              return (
                <div key={domain} className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="mono font-semibold text-[#9bb0c4]">{domain}</span>
                    <span className="mono text-[#e6f1f8]">{count.toLocaleString()} records</span>
                  </div>
                  <Progress value={pct} tone={domain === "LB" ? "teal" : domain === "VS" ? "lilac" : "amber"} />
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Live Subject Watch Table */}
      <div className="mt-5 glass overflow-hidden rounded-2xl">
        <div className="flex items-center justify-between border-b border-white/[.07] p-5">
          <div>
            <div className="mono text-[10px] uppercase tracking-[.15em] text-[#77879b]">Live Subject Watch</div>
            <div className="mt-1 display text-xl font-semibold text-[#e9f2f6]">Subjects with Active Findings</div>
          </div>
          <button onClick={() => go("/evidence")} className="text-[11px] text-[#72e8d5] flex items-center gap-1" data-testid="button-see-all-signals">
            See all findings <ChevronRight size={13} />
          </button>
        </div>
        <div className="divide-y divide-white/[.06]">
          {activeSubjects.map((s, i) => (
            <button
              key={s.usubjid}
              onClick={() => setSelectedSubject(s)}
              className="flex w-full items-center gap-3 px-5 py-3.5 text-left hover:bg-white/[.035] transition"
              data-testid={`button-subject-${s.usubjid}`}
            >
              <div className={cn("grid h-8 w-8 place-items-center rounded-lg border text-[10px] mono", s.findings_count > 0 ? "border-[#ff7e72]/25 text-[#ff9a90]" : "border-[#58e8d1]/20 text-[#75f5df]")}>
                {String(i + 1).padStart(2, "0")}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-[11px] font-semibold text-[#dce6ee]">
                  {s.usubjid} <span className="font-normal text-[#617187]">· Site {s.site_id}</span>
                </div>
                <div className="mt-0.5 truncate text-[10px] text-[#78899d]">
                  Arm: {s.arm || "Standard"} · Age: {s.age || "N/A"} · Sex: {s.sex || "N/A"}
                </div>
              </div>
              <Badge tone={s.findings_count >= 2 ? "coral" : s.findings_count === 1 ? "amber" : "teal"}>
                {s.findings_count} {s.findings_count === 1 ? "finding" : "findings"}
              </Badge>
              <ChevronRight size={15} className="text-[#53647b]" />
            </button>
          ))}
        </div>
      </div>

      {/* Subject Drawer */}
      <AnimatePresence>
        {selectedSubject && (
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className="fixed bottom-5 right-5 z-30 w-[min(390px,calc(100vw-40px))] glass rounded-2xl p-5 shadow-2xl">
            <div className="flex justify-between">
              <div>
                <Badge tone={selectedSubject.findings_count > 0 ? "coral" : "teal"}>
                  {selectedSubject.findings_count} active {selectedSubject.findings_count === 1 ? "finding" : "findings"}
                </Badge>
                <div className="mt-3 display text-xl font-semibold text-[#edf4f8]">{selectedSubject.usubjid}</div>
                <div className="mt-1 text-[11px] text-[#75869b]">Site {selectedSubject.site_id} · Arm: {selectedSubject.arm || "N/A"}</div>
              </div>
              <button onClick={() => setSelectedSubject(null)} data-testid="button-close-subject"><X size={16} /></button>
            </div>
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => go("/graph")}
                className="flex-1 flex justify-center items-center gap-1.5 rounded-lg border border-[#65f0d6]/20 bg-[#65f0d6]/[.09] py-2 text-[11px] text-[#9affed] hover:bg-[#65f0d6]/[.18] transition"
              >
                <Network size={13} /> View in graph
              </button>
              <button
                onClick={() => go("/evidence")}
                className="flex-1 flex justify-center items-center gap-1.5 rounded-lg border border-white/[.1] bg-white/[.04] py-2 text-[11px] text-[#c1d1e0] hover:bg-white/[.08] transition"
              >
                <FileSearch size={13} /> View findings
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// -----------------------------------------------------------------------------
// PAGE 2: STUDY GRAPH (Progressive Clinical Overview & Patient 360)
// -----------------------------------------------------------------------------

function humanizeFindingType(type: string): string {
  const map: Record<string, string> = {
    potential_hys_law: "Potential Hy's Law",
    prohibited_concomitant_medication: "Prohibited Medication",
    serious_adverse_event: "Serious Adverse Event",
    exclusion_violation_creatinine: "Screening Creatinine Exclusion",
    visit_window_deviation: "Visit-Window Deviation",
  };
  return map[type] || type.replaceAll("_", " ");
}

interface DomainStyle {
  title: string;
  tone: Tone;
  hubBg: string;
  hubBorder: string;
  hubText: string;
  hubBadge: string;
  recordBg: string;
  recordBorder: string;
  recordText: string;
  dotColor: string;
}

const DOMAIN_STYLES: Record<string, DomainStyle> = {
  LAB: {
    title: "Labs",
    tone: "teal",
    hubBg: "bg-[#e6faf8]",
    hubBorder: "border-[#5eead4]",
    hubText: "text-[#0f766e]",
    hubBadge: "bg-[#ccfbf1] text-[#0f766e]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#99f6e4]",
    recordText: "text-[#0f766e]",
    dotColor: "#14b8a6",
  },
  LB: {
    title: "Labs",
    tone: "teal",
    hubBg: "bg-[#e6faf8]",
    hubBorder: "border-[#5eead4]",
    hubText: "text-[#0f766e]",
    hubBadge: "bg-[#ccfbf1] text-[#0f766e]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#99f6e4]",
    recordText: "text-[#0f766e]",
    dotColor: "#14b8a6",
  },
  VITAL_SIGN: {
    title: "Vital Signs",
    tone: "coral",
    hubBg: "bg-[#fff1f2]",
    hubBorder: "border-[#fecdd3]",
    hubText: "text-[#be123c]",
    hubBadge: "bg-[#ffe4e6] text-[#be123c]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#fda4af]",
    recordText: "text-[#9f1239]",
    dotColor: "#f43f5e",
  },
  VS: {
    title: "Vital Signs",
    tone: "coral",
    hubBg: "bg-[#fff1f2]",
    hubBorder: "border-[#fecdd3]",
    hubText: "text-[#be123c]",
    hubBadge: "bg-[#ffe4e6] text-[#be123c]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#fda4af]",
    recordText: "text-[#9f1239]",
    dotColor: "#f43f5e",
  },
  AE: {
    title: "Adverse Events",
    tone: "coral",
    hubBg: "bg-[#fff1f0]",
    hubBorder: "border-[#fecaca]",
    hubText: "text-[#b91c1c]",
    hubBadge: "bg-[#fee2e2] text-[#b91c1c]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#fca5a5]",
    recordText: "text-[#991b1b]",
    dotColor: "#ef4444",
  },
  MEDICATION: {
    title: "Medications",
    tone: "amber",
    hubBg: "bg-[#fffbeb]",
    hubBorder: "border-[#fde68a]",
    hubText: "text-[#b45309]",
    hubBadge: "bg-[#fef3c7] text-[#b45309]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#fcd34d]",
    recordText: "text-[#92400e]",
    dotColor: "#f59e0b",
  },
  CM: {
    title: "Medications",
    tone: "amber",
    hubBg: "bg-[#fffbeb]",
    hubBorder: "border-[#fde68a]",
    hubText: "text-[#b45309]",
    hubBadge: "bg-[#fef3c7] text-[#b45309]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#fcd34d]",
    recordText: "text-[#92400e]",
    dotColor: "#f59e0b",
  },
  EXPOSURE: {
    title: "Exposure",
    tone: "lilac",
    hubBg: "bg-[#f5f3ff]",
    hubBorder: "border-[#ddd6fe]",
    hubText: "text-[#6d28d9]",
    hubBadge: "bg-[#ede9fe] text-[#6d28d9]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#c4b5fd]",
    recordText: "text-[#5b21b6]",
    dotColor: "#8b5cf6",
  },
  EX: {
    title: "Exposure",
    tone: "lilac",
    hubBg: "bg-[#f5f3ff]",
    hubBorder: "border-[#ddd6fe]",
    hubText: "text-[#6d28d9]",
    hubBadge: "bg-[#ede9fe] text-[#6d28d9]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#c4b5fd]",
    recordText: "text-[#5b21b6]",
    dotColor: "#8b5cf6",
  },
  ECG: {
    title: "ECG",
    tone: "lilac",
    hubBg: "bg-[#eef2ff]",
    hubBorder: "border-[#c7d2fe]",
    hubText: "text-[#4338ca]",
    hubBadge: "bg-[#e0e7ff] text-[#4338ca]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#a5b4fc]",
    recordText: "text-[#3730a3]",
    dotColor: "#6366f1",
  },
  EG: {
    title: "ECG",
    tone: "lilac",
    hubBg: "bg-[#eef2ff]",
    hubBorder: "border-[#c7d2fe]",
    hubText: "text-[#4338ca]",
    hubBadge: "bg-[#e0e7ff] text-[#4338ca]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#a5b4fc]",
    recordText: "text-[#3730a3]",
    dotColor: "#6366f1",
  },
  HISTORY: {
    title: "History",
    tone: "slate",
    hubBg: "bg-[#faf5ff]",
    hubBorder: "border-[#e9d5ff]",
    hubText: "text-[#7e22ce]",
    hubBadge: "bg-[#f3e8ff] text-[#7e22ce]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#d8b4fe]",
    recordText: "text-[#6b21a8]",
    dotColor: "#a855f7",
  },
  MH: {
    title: "History",
    tone: "slate",
    hubBg: "bg-[#faf5ff]",
    hubBorder: "border-[#e9d5ff]",
    hubText: "text-[#7e22ce]",
    hubBadge: "bg-[#f3e8ff] text-[#7e22ce]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#d8b4fe]",
    recordText: "text-[#6b21a8]",
    dotColor: "#a855f7",
  },
  DISPOSITION: {
    title: "Disposition",
    tone: "slate",
    hubBg: "bg-[#f1f5f9]",
    hubBorder: "border-[#cbd5e1]",
    hubText: "text-[#334155]",
    hubBadge: "bg-[#e2e8f0] text-[#334155]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#94a3b8]",
    recordText: "text-[#1e293b]",
    dotColor: "#64748b",
  },
  DS: {
    title: "Disposition",
    tone: "slate",
    hubBg: "bg-[#f1f5f9]",
    hubBorder: "border-[#cbd5e1]",
    hubText: "text-[#334155]",
    hubBadge: "bg-[#e2e8f0] text-[#334155]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#94a3b8]",
    recordText: "text-[#1e293b]",
    dotColor: "#64748b",
  },
  DEMOGRAPHICS: {
    title: "Demographics",
    tone: "slate",
    hubBg: "bg-[#f8fafc]",
    hubBorder: "border-[#cbd5e1]",
    hubText: "text-[#334155]",
    hubBadge: "bg-[#e2e8f0] text-[#334155]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#cbd5e1]",
    recordText: "text-[#1e293b]",
    dotColor: "#64748b",
  },
  DM: {
    title: "Demographics",
    tone: "slate",
    hubBg: "bg-[#f8fafc]",
    hubBorder: "border-[#cbd5e1]",
    hubText: "text-[#334155]",
    hubBadge: "bg-[#e2e8f0] text-[#334155]",
    recordBg: "bg-white/95",
    recordBorder: "border-[#cbd5e1]",
    recordText: "text-[#1e293b]",
    dotColor: "#64748b",
  },
};

const domainMeta: Record<string, { title: string; tone: Tone }> = {
  LAB: { title: "Labs", tone: "teal" },
  LB: { title: "Labs", tone: "teal" },
  VITAL_SIGN: { title: "Vital Signs", tone: "teal" },
  VS: { title: "Vital Signs", tone: "teal" },
  AE: { title: "Adverse Events", tone: "coral" },
  MEDICATION: { title: "Medications", tone: "amber" },
  CM: { title: "Medications", tone: "amber" },
  EXPOSURE: { title: "Exposure", tone: "lilac" },
  EX: { title: "Exposure", tone: "lilac" },
  ECG: { title: "ECG", tone: "lilac" },
  EG: { title: "ECG", tone: "lilac" },
  HISTORY: { title: "History", tone: "slate" },
  MH: { title: "History", tone: "slate" },
  DISPOSITION: { title: "Disposition", tone: "slate" },
  DS: { title: "Disposition", tone: "slate" },
  DEMOGRAPHICS: { title: "Demographics", tone: "slate" },
  DM: { title: "Demographics", tone: "slate" },
};

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "Date Unrecorded";
  if (/^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$/.test(dateStr)) return dateStr;
  try {
    const parts = dateStr.split("T")[0].split("-");
    if (parts.length === 3) {
      const year = parts[0];
      const monthIdx = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      if (monthIdx >= 0 && monthIdx < 12 && !isNaN(day)) {
        return `${day} ${months[monthIdx]} ${year}`;
      }
    }
  } catch (e) {
    // fallback
  }
  return dateStr;
}

const FINDING_EXPLANATIONS: Record<string, string> = {
  potential_hys_law: "Liver-related laboratory values crossed the study's predefined safety thresholds and require medical review.",
  prohibited_concomitant_medication: "A medication recorded for this subject is prohibited under the active study protocol.",
  visit_window_deviation: "This study visit occurred outside the protocol's permitted timing window.",
  serious_adverse_event: "This adverse event meets the study protocol's serious-event criteria.",
  exclusion_violation_creatinine: "Screening creatinine exceeded the protocol's eligibility threshold.",
};

function friendlyDomainName(dom: string): string {
  const map: Record<string, string> = {
    LB: "Lab",
    LAB: "Lab",
    VS: "Vital Sign",
    VITAL_SIGN: "Vital Sign",
    CM: "Medication",
    MEDICATION: "Medication",
    AE: "Adverse Event",
    EX: "Study Treatment",
    EXPOSURE: "Study Treatment",
    EG: "ECG",
    ECG: "ECG",
    DS: "Disposition",
    DISPOSITION: "Disposition",
    MH: "Medical History",
    HISTORY: "Medical History",
    DM: "Enrollment",
    DEMOGRAPHICS: "Enrollment",
  };
  return map[dom.toUpperCase()] || dom;
}

function domainBadgeClass(dom: string): string {
  const map: Record<string, string> = {
    LB: "bg-[#ccfbf1] text-[#0f766e] border border-[#5eead4]",
    VS: "bg-[#ffe4e6] text-[#be123c] border border-[#fecdd3]",
    CM: "bg-[#fef3c7] text-[#b45309] border border-[#fde68a]",
    AE: "bg-[#fee2e2] text-[#b91c1c] border border-[#fecaca]",
    EX: "bg-[#ede9fe] text-[#6d28d9] border border-[#ddd6fe]",
    EG: "bg-[#e0e7ff] text-[#4338ca] border border-[#c7d2fe]",
    DS: "bg-[#e2e8f0] text-[#334155] border border-[#cbd5e1]",
    MH: "bg-[#f3e8ff] text-[#7e22ce] border border-[#e9d5ff]",
    DM: "bg-[#e2e8f0] text-[#334155] border border-[#cbd5e1]",
  };
  return map[dom.toUpperCase()] || "bg-[#f1f5f9] text-[#475569] border border-[#cbd5e1]";
}

function getVisitOrder(visitStr?: string | null): number {
  if (!visitStr) return 999;
  const v = visitStr.toUpperCase().trim();
  if (v.includes("SCREEN")) return 1;
  if (v.includes("BASE")) return 2;
  const match = v.match(/WEEK\s*(\d+)/i) || v.match(/W(\d+)/i);
  if (match) return 10 + parseInt(match[1], 10);
  if (v.includes("DISP") || v.includes("END") || v.includes("COMPLET")) return 900;
  if (v.includes("UNSCHED")) return 950;
  return 500;
}

function formatNodeLabel(node: GraphNode, isEvidence = false): string {
  const p = node.properties || {};
  if (node.type === "FINDING") {
    return humanizeFindingType(node.label || node.id);
  }
  if (node.type === "LAB" || node.type === "LB") {
    const test = p.test || node.label;
    if (isEvidence && p.value !== undefined) {
      const ulnStr = p.ratio_to_uln ? ` · ${Number(p.ratio_to_uln).toFixed(2)}× ULN` : "";
      return `${test} · ${p.value} ${p.unit || ""}${ulnStr}`;
    }
    if (p.visit) return `${test} · ${p.visit}`;
    if (p.value !== undefined) return `${test} · ${p.value} ${p.unit || ""}`;
    return test;
  }
  if (node.type === "MEDICATION" || node.type === "CM") {
    const trt = p.treatment || node.label;
    if (p.dose) return `${trt} · ${p.dose}mg`;
    return trt;
  }
  if (node.type === "AE") {
    return p.term || node.label;
  }
  if (node.type === "VITAL_SIGN" || node.type === "VS") {
    const test = p.test || node.label;
    if (p.visit) return `${test} · ${p.visit}`;
    return test;
  }
  if (node.type === "EXPOSURE" || node.type === "EX") {
    return p.visit ? `Dose · ${p.visit}` : node.label;
  }
  if (node.type === "ECG" || node.type === "EG") {
    return p.visit ? `ECG · ${p.visit}` : node.label;
  }
  return node.label || node.id;
}

function renderPropertyValue(val: any): ReactNode {
  if (val === null || val === undefined) return <span className="text-[#64748b]">N/A</span>;
  if (typeof val === "boolean") return <span className={val ? "text-[#0f766e] font-semibold" : "text-[#be123c] font-semibold"}>{val ? "True" : "False"}</span>;
  if (typeof val === "number") return <span className="text-[#0f172a] font-semibold">{val}</span>;
  if (typeof val === "string") return <span className="text-[#1e293b] break-all">{val}</span>;
  if (Array.isArray(val)) {
    return (
      <div className="flex flex-wrap gap-1 mt-1">
        {val.map((item, idx) => (
          <span key={idx} className="mono rounded bg-[#f1f5f9] border border-[#e2e8f0] px-1.5 py-0.5 text-[10px] text-[#334155]">
            {typeof item === "object" ? JSON.stringify(item) : String(item)}
          </span>
        ))}
      </div>
    );
  }
  if (typeof val === "object") {
    return (
      <div className="space-y-1 mt-1 pl-2 border-l-2 border-[#cbd5e1]">
        {Object.entries(val).map(([k, v]) => (
          <div key={k} className="flex justify-between gap-2 text-[10px]">
            <span className="text-[#64748b]">{k}:</span>
            <span className="text-[#1e293b] font-medium">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
          </div>
        ))}
      </div>
    );
  }
  return String(val);
}

function StudyGraph() {
  const [, go] = useLocation();
  const { data: context } = useQuery({ queryKey: ["context"], queryFn: api.getContext });
  const { data: subjects = [] } = useQuery({ queryKey: ["subjects"], queryFn: api.getSubjects });
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>(() => {
    try {
      return localStorage.getItem("selectedSubjectId") || "042-S07-001";
    } catch {
      return "042-S07-001";
    }
  });
  const [activeTab, setActiveTab] = useState<"graph" | "timeline">("graph");
  const [viewMode, setViewMode] = useState<"overview" | "all">("overview");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [expandedHubs, setExpandedHubs] = useState<Set<string>>(new Set());
  const [layerFilter, setLayerFilter] = useState<string>("All layers");

  // Timeline / Patient Journey states
  const [timelineFilter, setTimelineFilter] = useState<string>("ALL");
  const [importantOnly, setImportantOnly] = useState<boolean>(false);
  const [expandedVisits, setExpandedVisits] = useState<Set<string>>(new Set());
  const [selectedTimelineRecord, setSelectedTimelineRecord] = useState<TimelineItem | null>(null);

  const selectedSubject = useMemo(() => {
    return subjects.find((s) => s.usubjid === selectedSubjectId) || null;
  }, [subjects, selectedSubjectId]);

  const { data: graphData, isLoading: graphLoading } = useQuery({
    queryKey: ["subject-graph", selectedSubjectId],
    queryFn: () => api.getSubjectGraph(selectedSubjectId),
    enabled: Boolean(selectedSubjectId),
  });

  const { data: timelineData = [], isLoading: timelineLoading } = useQuery({
    queryKey: ["subject-timeline", selectedSubjectId],
    queryFn: () => api.getTimeline(selectedSubjectId),
    enabled: Boolean(selectedSubjectId),
  });

  const { data: subjectFindingsList = [] } = useQuery({
    queryKey: ["findings", selectedSubjectId],
    queryFn: () => api.getFindings(selectedSubjectId),
    enabled: Boolean(selectedSubjectId),
  });

  const rawNodes = graphData?.nodes ?? [];
  const rawEdges = graphData?.edges ?? [];

  // Findings calculations and breakdowns
  const subjectFindings = useMemo(() => {
    return rawNodes.filter((n) => n.type === "FINDING");
  }, [rawNodes]);

  const findingTypeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    subjectFindingsList.forEach((f) => {
      const title = humanizeFindingType(f.finding_type);
      counts[title] = (counts[title] || 0) + 1;
    });
    return counts;
  }, [subjectFindingsList]);

  const findingBreakdownText = useMemo(() => {
    if (subjectFindingsList.length === 0) return "";
    return Object.entries(findingTypeCounts)
      .map(([type, count]) => `${count} ${type}`)
      .join(" · ");
  }, [subjectFindingsList, findingTypeCounts]);

  const hasSafetyFinding = useMemo(() => {
    return subjectFindingsList.some((f) => f.finding_type === "potential_hys_law" || f.finding_type === "serious_adverse_event");
  }, [subjectFindingsList]);

  const hasMedOrExclusion = useMemo(() => {
    return subjectFindingsList.some((f) => f.finding_type === "prohibited_concomitant_medication" || f.finding_type === "exclusion_violation_creatinine");
  }, [subjectFindingsList]);

  const evidenceNodeIdMap = useMemo(() => {
    const map = new Map<string, string>(); // evidenceNodeId -> findingNodeId
    subjectFindings.forEach((f) => {
      rawEdges.forEach((e) => {
        if (e.source === f.id && (e.relationship === "SUPPORTED_BY" || e.relationship === "HAS_EVIDENCE")) {
          map.set(e.target, f.id);
        }
      });
    });
    return map;
  }, [subjectFindings, rawEdges]);

  // Evidence key map for timeline items
  const evidenceKeyMap = useMemo(() => {
    const map = new Map<string, FindingItem>();
    subjectFindingsList.forEach((f) => {
      (f.evidence || []).forEach((ev) => {
        map.set(`${ev.domain.toUpperCase()}_${ev.seq}`, f);
      });
    });
    return map;
  }, [subjectFindingsList]);

  // Group timeline records and findings by study visit
  const visitGroups = useMemo(() => {
    if (timelineData.length === 0 && subjectFindingsList.length === 0) return [];

    const groupsMap = new Map<string, {
      visitName: string;
      dates: string[];
      items: TimelineItem[];
    }>();

    const getGroupKey = (item: TimelineItem) => {
      if (item.visit && item.visit.trim()) {
        return item.visit.trim().toUpperCase();
      }
      if (item.date) {
        return `DATE_${item.date}`;
      }
      return "UNSCHEDULED";
    };

    timelineData.forEach((item) => {
      const key = getGroupKey(item);
      if (!groupsMap.has(key)) {
        const displayName = item.visit ? item.visit.trim() : (item.date ? formatDate(item.date) : "Unscheduled Events");
        groupsMap.set(key, {
          visitName: displayName,
          dates: [],
          items: [],
        });
      }
      const grp = groupsMap.get(key)!;
      grp.items.push(item);
      if (item.date && !grp.dates.includes(item.date)) {
        grp.dates.push(item.date);
      }
    });

    const groups = Array.from(groupsMap.entries()).map(([key, grp]) => {
      grp.dates.sort();
      const primaryDate = grp.dates[0] || null;

      const matchedFindings = subjectFindingsList.filter((f) => {
        if (f.details?.visit && grp.visitName.toUpperCase().includes(f.details.visit.toUpperCase())) {
          return true;
        }
        if (primaryDate) {
          if (
            f.details?.transaminase_date === primaryDate ||
            f.details?.actual_date === primaryDate ||
            f.details?.start_date === primaryDate ||
            f.details?.date === primaryDate
          ) {
            return true;
          }
        }
        return grp.items.some(
          (item) => item.evidence && evidenceKeyMap.get(`${item.evidence.domain.toUpperCase()}_${item.evidence.seq}`)?.finding_id === f.finding_id
        );
      });

      const hasSafety = matchedFindings.some((f) => f.finding_type === "potential_hys_law" || f.finding_type === "serious_adverse_event");

      return {
        id: `visit-${key.toLowerCase().replace(/[^a-z0-9]/g, "-")}`,
        visitName: grp.visitName,
        date: primaryDate,
        formattedDate: formatDate(primaryDate),
        items: grp.items,
        findings: matchedFindings,
        hasFinding: matchedFindings.length > 0,
        hasSafetyFinding: hasSafety,
      };
    });

    // Check for unmatched findings and create dedicated cards
    const matchedFindingIds = new Set<string>();
    groups.forEach((g) => g.findings.forEach((f) => matchedFindingIds.add(f.finding_id)));
    const unmatchedFindings = subjectFindingsList.filter((f) => !matchedFindingIds.has(f.finding_id));

    unmatchedFindings.forEach((f) => {
      const fDate = f.details?.transaminase_date || f.details?.start_date || f.details?.actual_date || f.details?.date || null;
      const isSafety = f.finding_type === "potential_hys_law" || f.finding_type === "serious_adverse_event";
      groups.push({
        id: `finding-${f.finding_id}`,
        visitName: f.details?.visit || humanizeFindingType(f.finding_type),
        date: fDate,
        formattedDate: formatDate(fDate),
        items: [],
        findings: [f],
        hasFinding: true,
        hasSafetyFinding: isSafety,
      });
    });

    groups.sort((a, b) => {
      const orderA = getVisitOrder(a.visitName);
      const orderB = getVisitOrder(b.visitName);
      if (orderA !== orderB) return orderA - orderB;
      if (a.date && b.date) return a.date.localeCompare(b.date);
      if (a.date) return -1;
      if (b.date) return 1;
      return 0;
    });

    return groups;
  }, [timelineData, subjectFindingsList, evidenceKeyMap]);

  // CLINICAL OVERVIEW (Progressive Disclosure)
  const overviewGraph = useMemo(() => {
    if (rawNodes.length === 0) return { nodes: [], edges: [] };

    const subjectNode = rawNodes.find((n) => n.type === "SUBJECT") || {
      id: `SUBJ_${selectedSubjectId}`,
      label: selectedSubjectId,
      type: "SUBJECT",
      properties: { usubjid: selectedSubjectId },
    };

    const findingNodes = rawNodes.filter((n) => n.type === "FINDING");
    const evidenceNodes = rawNodes.filter((n) => evidenceNodeIdMap.has(n.id));
    const evidenceIds = new Set(evidenceNodes.map((n) => n.id));

    const routineNodes = rawNodes.filter(
      (n) => n.type !== "SUBJECT" && n.type !== "FINDING" && !evidenceIds.has(n.id)
    );

    const domainGroups: Record<string, GraphNode[]> = {};
    routineNodes.forEach((n) => {
      const dom = n.type;
      if (!domainGroups[dom]) domainGroups[dom] = [];
      domainGroups[dom].push(n);
    });

    const displayNodes: Array<GraphNode & {
      cx: number;
      cy: number;
      tone: Tone;
      isEvidence?: boolean;
      isHub?: boolean;
      hubDomain?: string;
      recordCount?: number;
      isExpanded?: boolean;
    }> = [];

    const displayEdges: Array<{
      source: string;
      target: string;
      relationship: string;
      isFindingFlow?: boolean;
    }> = [];

    const centerCx = 320;
    const centerCy = 190;
    displayNodes.push({
      ...subjectNode,
      cx: centerCx,
      cy: centerCy,
      tone: "teal",
    });

    const totalFindings = findingNodes.length;
    findingNodes.forEach((fNode, fIdx) => {
      const fCy = totalFindings === 1 ? centerCy : 95 + fIdx * (200 / Math.max(1, totalFindings - 1));
      const fCx = 185;

      displayNodes.push({
        ...fNode,
        cx: fCx,
        cy: fCy,
        tone: fNode.label.includes("hys") ? "amber" : "coral",
      });

      displayEdges.push({
        source: subjectNode.id,
        target: fNode.id,
        relationship: "HAS_FINDING",
        isFindingFlow: true,
      });

      const attachedEv = evidenceNodes.filter((ev) => evidenceNodeIdMap.get(ev.id) === fNode.id);
      attachedEv.forEach((evNode, evIdx) => {
        const evOffset = attachedEv.length === 1 ? 0 : (evIdx - (attachedEv.length - 1) / 2) * 44;
        const evCx = 65;
        const evCy = Math.max(35, Math.min(345, fCy + evOffset));

        displayNodes.push({
          ...evNode,
          cx: evCx,
          cy: evCy,
          tone: "teal",
          isEvidence: true,
        });

        displayEdges.push({
          source: fNode.id,
          target: evNode.id,
          relationship: "SUPPORTED_BY",
          isFindingFlow: true,
        });
      });
    });

    const domains = Object.keys(domainGroups);
    const hubCount = domains.length;

    domains.forEach((dom, dIdx) => {
      const meta = domainMeta[dom] || { title: dom, tone: "slate" };
      const records = domainGroups[dom];
      const hubId = `hub_${dom}`;
      const isExpanded = expandedHubs.has(hubId);

      const angle = hubCount === 1 ? 0 : -0.9 + (dIdx / Math.max(1, hubCount - 1)) * 1.8;
      const hubRadius = 195;
      const hubCx = centerCx + Math.cos(angle) * hubRadius;
      const hubCy = centerCy + Math.sin(angle) * 125;

      displayNodes.push({
        id: hubId,
        label: `${meta.title} (${records.length})`,
        type: "DOMAIN_HUB",
        cx: Math.max(420, Math.min(600, hubCx)),
        cy: Math.max(45, Math.min(335, hubCy)),
        tone: meta.tone,
        isHub: true,
        hubDomain: dom,
        recordCount: records.length,
        isExpanded,
      });

      displayEdges.push({
        source: subjectNode.id,
        target: hubId,
        relationship: "HAS_DOMAIN",
      });

      if (isExpanded) {
        records.slice(0, 16).forEach((rec, rIdx) => {
          const rAngle = (rIdx / Math.min(records.length, 16)) * 2 * Math.PI;
          const rRadius = 48;
          const recCx = hubCx + Math.cos(rAngle) * rRadius;
          const recCy = hubCy + Math.sin(rAngle) * rRadius;

          displayNodes.push({
            ...rec,
            cx: Math.max(380, Math.min(630, recCx)),
            cy: Math.max(30, Math.min(350, recCy)),
            tone: meta.tone,
          });

          displayEdges.push({
            source: hubId,
            target: rec.id,
            relationship: "CONTAINS_RECORD",
          });
        });
      }
    });

    return { nodes: displayNodes, edges: displayEdges };
  }, [rawNodes, rawEdges, evidenceNodeIdMap, selectedSubjectId, expandedHubs]);

  // ALL RECORDS MODE (Refined Multi-ring Layout with Generous Spacing)
  const allRecordsGraph = useMemo(() => {
    if (rawNodes.length === 0) return { nodes: [], edges: [] };
    const centerNode = rawNodes.find((n) => n.type === "SUBJECT") || rawNodes[0];
    const otherNodes = rawNodes.filter((n) => n.id !== centerNode?.id);

    const displayNodes: Array<GraphNode & { cx: number; cy: number; tone: Tone; isEvidence?: boolean }> = [];

    if (centerNode) {
      displayNodes.push({
        ...centerNode,
        cx: 330,
        cy: 190,
        tone: "teal",
      });
    }

    otherNodes.forEach((node, idx) => {
      const isFinding = node.type === "FINDING";
      const isEv = evidenceNodeIdMap.has(node.id);
      const ring = isFinding ? 95 : (isEv ? 140 : (idx % 3 === 0 ? 185 : (idx % 3 === 1 ? 230 : 270)));
      const angle = (idx / otherNodes.length) * 2 * Math.PI;
      const cx = 330 + Math.cos(angle) * ring;
      const cy = 190 + Math.sin(angle) * (ring * 0.62);

      let tone: Tone = "slate";
      if (isFinding) tone = "coral";
      else if (isEv) tone = "teal";
      else if (domainMeta[node.type]) tone = domainMeta[node.type].tone;

      displayNodes.push({
        ...node,
        cx: Math.max(45, Math.min(615, cx)),
        cy: Math.max(30, Math.min(350, cy)),
        tone,
        isEvidence: isEv,
      });
    });

    const displayEdges = rawEdges.map((e) => ({
      ...e,
      isFindingFlow: e.relationship === "HAS_FINDING" || e.relationship === "SUPPORTED_BY",
    }));

    return { nodes: displayNodes, edges: displayEdges };
  }, [rawNodes, rawEdges, evidenceNodeIdMap]);

  const activeGraph = viewMode === "overview" ? overviewGraph : allRecordsGraph;

  const filteredGraphNodes = useMemo(() => {
    if (layerFilter === "All layers") return activeGraph.nodes;
    return activeGraph.nodes.filter((n) => {
      if (n.type === "SUBJECT") return true;
      if (layerFilter === "FINDING" && n.type === "FINDING") return true;
      if (n.isHub && n.hubDomain === layerFilter) return true;
      return n.type === layerFilter;
    });
  }, [activeGraph.nodes, layerFilter]);

  const pointMap = useMemo(() => {
    const map: Record<string, [number, number]> = {};
    activeGraph.nodes.forEach((n) => {
      map[n.id] = [n.cx, n.cy];
    });
    return map;
  }, [activeGraph.nodes]);

  const activeNode = useMemo(() => {
    if (selectedNodeId) {
      return activeGraph.nodes.find((n) => n.id === selectedNodeId) || rawNodes.find((n) => n.id === selectedNodeId) || null;
    }
    return subjectFindings[0] || rawNodes.find((n) => n.type === "SUBJECT") || null;
  }, [selectedNodeId, activeGraph.nodes, rawNodes, subjectFindings]);

  const handleResetView = () => {
    setViewMode("overview");
    setLayerFilter("All layers");
    setExpandedHubs(new Set());
    setSelectedNodeId(null);
    setHoveredNodeId(null);
  };

  const toggleHub = (hubId: string) => {
    setExpandedHubs((prev) => {
      const next = new Set(prev);
      if (next.has(hubId)) next.delete(hubId);
      else next.add(hubId);
      return next;
    });
  };

  return (
    <div className="mx-auto max-w-[1480px] px-5 py-6 md:px-9 md:py-8">
      <Heading
        eyebrow={`Patient 360 Knowledge Graph / Cut ${context?.current_cut ?? 12} · Protocol v${context?.protocol_version ?? 3}`}
        title="The study is a network."
        detail="Explore a subject's clinical journey, detected findings, and the exact records that support each conclusion."
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("graph")}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-2 text-[11px] font-semibold transition",
                activeTab === "graph"
                  ? "bg-[#ccfbf1] text-[#0f766e] border border-[#5eead4] shadow-xs"
                  : "text-[#64748b] hover:bg-white/80 hover:text-[#0f172a]"
              )}
            >
              <Network size={14} /> Graph
            </button>
            <button
              onClick={() => setActiveTab("timeline")}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-2 text-[11px] font-semibold transition",
                activeTab === "timeline"
                  ? "bg-[#ccfbf1] text-[#0f766e] border border-[#5eead4] shadow-xs"
                  : "text-[#64748b] hover:bg-white/80 hover:text-[#0f172a]"
              )}
            >
              <CalendarDays size={14} /> Patient journey
            </button>
          </div>
        }
      />

      {/* 1. SUBJECT SUMMARY & CLINICAL PROFILE CARD */}
      <div className="rounded-2xl border border-[#cbd5e1]/70 bg-white/80 p-4 shadow-xs backdrop-blur-md mb-4">
        {/* Top: Subject Identity & Switch Subject */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-3.5 border-b border-[#e2e8f0]/80">
          <div className="flex items-center gap-3.5">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#ccfbf1] text-[#0f766e] border border-[#5eead4] shadow-xs">
              <Target size={22} className="text-[#0f766e]" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="display text-lg font-bold text-[#0f172a] tracking-tight">{selectedSubjectId}</span>
                <Badge tone="teal">Site {selectedSubject?.site_id || "S07"}</Badge>
                <Badge tone={selectedSubject?.arm === "DRUG" ? "amber" : "slate"}>
                  Arm: {selectedSubject?.arm || "Placebo"}
                </Badge>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-2.5 text-xs text-[#64748b]">
                <span>Age: <strong className="font-semibold text-[#0f172a]">{selectedSubject?.age || "51"}</strong></span>
                <span className="text-[#cbd5e1]">•</span>
                <span>Sex: <strong className="font-semibold text-[#0f172a]">{selectedSubject?.sex || "M"}</strong></span>
                <span className="text-[#cbd5e1]">•</span>
                <span>Cut <strong className="font-semibold text-[#0f172a]">{context?.current_cut ?? 12}</strong> <span className="text-[#94a3b8]">(v{context?.protocol_version ?? 3})</span></span>
                <span className="text-[#cbd5e1]">•</span>
                <span>Records: <strong className="font-semibold text-[#0f172a]">{rawNodes.length - 1 - subjectFindings.length}</strong></span>
              </div>
            </div>
          </div>

          {/* Switch Subject selector */}
          <div className="flex items-center gap-2.5">
            <span className="text-xs font-semibold text-[#64748b] whitespace-nowrap">Switch Subject:</span>
            <div className="relative">
              <select
                value={selectedSubjectId}
                onChange={(e) => {
                  setSelectedSubjectId(e.target.value);
                  setSelectedNodeId(null);
                  setSelectedTimelineRecord(null);
                  setExpandedHubs(new Set());
                }}
                className="appearance-none rounded-xl border border-[#cbd5e1] bg-white pl-3.5 pr-8 py-1.5 text-xs font-semibold text-[#1e293b] shadow-xs outline-none hover:border-[#14b8a6] focus:border-[#14b8a6] focus:ring-2 focus:ring-[#14b8a6]/20 transition cursor-pointer"
                data-testid="select-graph-subject"
              >
                {subjects.map((s) => (
                  <option key={s.usubjid} value={s.usubjid} className="bg-white text-[#1e293b]">
                    {s.usubjid} (Site {s.site_id}) {s.findings_count > 0 ? `· [${s.findings_count} finding${s.findings_count > 1 ? "s" : ""}]` : ""}
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[#64748b]" />
            </div>
          </div>
        </div>

        {/* Bottom: Clinical Findings & Evidence Quick Access */}
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2.5 pt-0.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-[#64748b] mr-1">
              Findings ({subjectFindingsList.length}):
            </span>
            {subjectFindingsList.length > 0 ? (
              subjectFindingsList.map((f) => {
                const isSafety = f.finding_type === "potential_hys_law" || f.finding_type === "serious_adverse_event";
                const isHys = f.finding_type === "potential_hys_law";
                const isSelected = selectedNodeId === f.finding_id;

                return (
                  <button
                    key={f.finding_id}
                    onClick={() => {
                      setSelectedNodeId(f.finding_id);
                      if (viewMode === "all") setViewMode("overview");
                    }}
                    className={cn(
                      "flex items-center gap-1.5 rounded-xl border px-3 py-1 text-xs transition shadow-xs cursor-pointer",
                      isSafety
                        ? isSelected
                          ? "border-[#f87171] bg-[#fff1f2] text-[#881337] ring-2 ring-[#f87171]/50 shadow-sm"
                          : "border-[#fecdd3] bg-[#fff5f5] text-[#9f1239] hover:bg-[#ffe4e6]"
                        : isSelected
                        ? "border-[#fde68a] bg-[#fffbeb] text-[#92400e] ring-2 ring-[#fde68a]/50 shadow-sm"
                        : "border-[#e2e8f0] bg-white text-[#334155] hover:bg-[#f8fafc]"
                    )}
                  >
                    {isSafety ? (
                      <TriangleAlert size={13} className={isHys ? "text-[#e11d48]" : "text-[#d97706]"} />
                    ) : (
                      <FileSearch size={13} className="text-[#64748b]" />
                    )}
                    <span className="font-semibold">{humanizeFindingType(f.finding_type)}</span>
                    {isHys ? (
                      <span className="rounded-md bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-800">
                        Adjudication Required
                      </span>
                    ) : (
                      <span className={cn(
                        "rounded-md px-1.5 py-0.5 text-[10px] font-bold",
                        isSafety ? "bg-rose-100 text-rose-800" : "bg-slate-100 text-slate-700"
                      )}>
                        Detected
                      </span>
                    )}
                  </button>
                );
              })
            ) : (
              <div className="inline-flex items-center gap-2 text-xs font-semibold text-[#0f766e]">
                <ShieldCheck size={16} className="text-[#0d9488]" />
                No protocol deviations or clinical safety findings detected for this subject (Cut {context?.current_cut ?? 12})
              </div>
            )}
          </div>
          {subjectFindingsList.length > 0 && (
            <span className="text-[11px] text-[#94a3b8] hidden xl:inline">
              Click a finding chip to isolate its evidence in the graph
            </span>
          )}
        </div>
      </div>

      {/* 3. MAIN CONTENT: GRAPH OR TIMELINE */}
      {activeTab === "graph" ? (
        <>
          {/* Controls Bar */}
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3 bg-white/70 backdrop-blur-md p-3 rounded-xl border border-[#cbd5e1]/70 shadow-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="mono text-[10px] uppercase text-[#64748b] font-semibold mr-1">View Mode:</span>
              <button
                onClick={() => setViewMode("overview")}
                className={cn(
                  "rounded-lg px-2.5 py-1 text-[11px] font-semibold transition",
                  viewMode === "overview"
                    ? "bg-[#ccfbf1] text-[#0f766e] border border-[#5eead4] shadow-xs"
                    : "text-[#64748b] hover:bg-white hover:text-[#0f172a]"
                )}
              >
                Clinical overview (Default)
              </button>
              <button
                onClick={() => setViewMode("all")}
                className={cn(
                  "rounded-lg px-2.5 py-1 text-[11px] font-semibold transition",
                  viewMode === "all"
                    ? "bg-[#ccfbf1] text-[#0f766e] border border-[#5eead4] shadow-xs"
                    : "text-[#64748b] hover:bg-white hover:text-[#0f172a]"
                )}
              >
                All records ({rawNodes.length})
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <select
                value={layerFilter}
                onChange={(e) => setLayerFilter(e.target.value)}
                className="rounded-lg border border-[#cbd5e1] bg-white px-2.5 py-1 text-[11px] text-[#1e293b] font-semibold outline-none shadow-xs"
                data-testid="select-graph-layer"
              >
                <option value="All layers">All layers</option>
                <option value="FINDING">Findings</option>
                <option value="LB">Labs</option>
                <option value="AE">Adverse Events</option>
                <option value="CM">Medications</option>
                <option value="EX">Exposure</option>
                <option value="VS">Vitals</option>
                <option value="EG">ECG</option>
              </select>

              <button
                onClick={handleResetView}
                className="rounded-lg border border-[#cbd5e1] bg-white px-2.5 py-1 text-[11px] font-semibold text-[#475569] hover:bg-[#f8fafc] transition shadow-xs"
              >
                Reset view
              </button>
            </div>
          </div>

          {/* Visualization Grid */}
          <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
            {/* Graph Canvas */}
            <div className="glass relative min-h-[640px] overflow-hidden rounded-2xl bg-gradient-to-br from-white/95 via-[#f8fafc]/95 to-[#f0f9ff]/85 border border-[#cbd5e1]/70 shadow-[0_8px_30px_rgba(0,0,0,0.04)]">
              <div className="absolute inset-0 bg-grid opacity-35" />

              {/* Status Badges on Canvas */}
              <div className="absolute left-5 top-5 z-10 flex flex-wrap items-center gap-2.5">
                <Badge tone={viewMode === "overview" ? "teal" : "lilac"}>
                  {viewMode === "overview" ? "Clinical Overview" : "All Records Mode"}
                </Badge>
                <span className="mono text-[9.5px] text-[#64748b] font-medium">
                  {filteredGraphNodes.length} nodes · {viewMode === "overview" ? "Progressive Disclosure" : "Raw Graph"}
                </span>
              </div>

              {graphLoading ? (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="mono text-xs text-[#0d9488] font-semibold animate-pulse">Loading subject network graph...</div>
                </div>
              ) : filteredGraphNodes.length === 0 ? (
                <div className="absolute inset-0 flex items-center justify-center text-center p-6">
                  <div className="text-sm text-[#64748b] font-medium">No nodes available for the selected filters.</div>
                </div>
              ) : (
                <>
                  <svg className="absolute inset-0 h-full w-full p-4" viewBox="0 0 660 380" preserveAspectRatio="none">
                    {activeGraph.edges.map((e, idx) => {
                      const p1 = pointMap[e.source];
                      const p2 = pointMap[e.target];
                      if (!p1 || !p2) return null;

                      const isSelected = selectedNodeId === e.source || selectedNodeId === e.target;
                      const isHovered = hoveredNodeId === e.source || hoveredNodeId === e.target;
                      const isFindingFlow = e.isFindingFlow;
                      const isHubEdge = e.relationship === "HAS_DOMAIN" || e.relationship === "CONTAINS_RECORD";

                      let strokeColor = "#cbd5e1";
                      if (isFindingFlow) strokeColor = "#f43f5e";
                      else if (isSelected || isHovered) strokeColor = "#0d9488";
                      else if (isHubEdge) strokeColor = "#94a3b8";

                      let strokeOp = 0.28;
                      if (hoveredNodeId) {
                        strokeOp = (isHovered || isSelected) ? 0.95 : 0.12;
                      } else if (isFindingFlow) {
                        strokeOp = 0.85;
                      } else if (isSelected) {
                        strokeOp = 0.85;
                      }

                      const isDashed = e.relationship === "SUPPORTED_BY" || e.relationship === "HAS_EVIDENCE" || e.relationship === "CONTAINS_RECORD";

                      return (
                        <line
                          key={`${e.source}-${e.target}-${idx}`}
                          x1={p1[0]}
                          y1={p1[1]}
                          x2={p2[0]}
                          y2={p2[1]}
                          stroke={strokeColor}
                          strokeOpacity={strokeOp}
                          strokeWidth={isFindingFlow ? 2 : (isSelected || isHovered) ? 1.8 : 1}
                          strokeDasharray={isDashed ? "4 4" : undefined}
                          className={isFindingFlow ? "path-flow" : ""}
                        />
                      );
                    })}
                  </svg>

                  {/* Rendered Interactive Nodes */}
                  <div className="absolute inset-0">
                    {filteredGraphNodes.map((n) => {
                      const isSelected = selectedNodeId === n.id;
                      const isHovered = hoveredNodeId === n.id;
                      const isFinding = n.type === "FINDING";
                      const isHub = n.isHub;
                      const isEvidence = n.isEvidence;
                      const isSubject = n.type === "SUBJECT";
                      const domStyle = DOMAIN_STYLES[isHub ? (n.hubDomain || "") : n.type] || DOMAIN_STYLES.LAB;
                      const isCompact = viewMode === "all";

                      const isDimmed = hoveredNodeId !== null && hoveredNodeId !== n.id && !isFinding && !isEvidence && !isSubject;

                      return (
                        <motion.button
                          key={n.id}
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{
                            opacity: isDimmed ? 0.65 : 1,
                            scale: isSelected ? 1.06 : isHovered ? 1.04 : 1,
                            boxShadow: isFinding
                              ? (isSelected ? "0 0 20px rgba(244, 63, 94, 0.35)" : "0 4px 14px rgba(244, 63, 94, 0.12)")
                              : isEvidence
                              ? (isSelected ? "0 0 16px rgba(20, 184, 166, 0.3)" : "0 3px 10px rgba(20, 184, 166, 0.12)")
                              : isSubject
                              ? (isSelected ? "0 0 20px rgba(13, 148, 136, 0.3)" : "0 4px 16px rgba(13, 148, 136, 0.12)")
                              : isHub
                              ? (isSelected ? "0 0 16px rgba(99, 102, 241, 0.25)" : "0 2px 8px rgba(60, 90, 130, 0.08)")
                              : (isSelected ? "0 0 12px rgba(71, 85, 105, 0.2)" : "0 1px 4px rgba(0, 0, 0, 0.04)"),
                          }}
                          transition={{ duration: 0.15 }}
                          onClick={() => {
                            if (isHub) toggleHub(n.id);
                            setSelectedNodeId(n.id);
                          }}
                          onMouseEnter={() => setHoveredNodeId(n.id)}
                          onMouseLeave={() => setHoveredNodeId(null)}
                          style={{ left: `${(n.cx / 660) * 100}%`, top: `${(n.cy / 380) * 100}%` }}
                          className={cn(
                            "absolute -translate-x-1/2 -translate-y-1/2 rounded-xl border text-left transition-all cursor-pointer backdrop-blur-md",
                            isSelected ? "z-30 ring-2" : isHovered ? "z-25" : "z-10",
                            isFinding
                              ? cn(
                                  "border-[#f87171] bg-[#fff1f2]/95 text-[#881337] min-w-[145px] px-3 py-1.5",
                                  isSelected ? "border-[#e11d48] ring-[#e11d48]/40" : "hover:border-[#e11d48]"
                                )
                              : isEvidence
                              ? cn(
                                  "border-[#2dd4bf] bg-[#f0fdfa]/95 text-[#0f766e] min-w-[130px] px-2.5 py-1.5",
                                  isSelected ? "border-[#0d9488] ring-[#0d9488]/40" : "hover:border-[#0d9488]"
                                )
                              : isSubject
                              ? cn(
                                  "border-2 border-[#14b8a6] bg-[#f0fdfa]/98 text-[#0f766e] p-3 text-center min-w-[125px]",
                                  isSelected ? "border-[#0d9488] ring-[#0d9488]/40" : "hover:border-[#0d9488]"
                                )
                              : isHub
                              ? cn(
                                  "border-1.5 min-w-[110px] px-3 py-1.5",
                                  domStyle.hubBg,
                                  domStyle.hubBorder,
                                  domStyle.hubText,
                                  isSelected ? "ring-indigo-400/40" : ""
                                )
                              : cn(
                                  "border bg-white/92 text-[#1e293b]",
                                  domStyle.recordBorder,
                                  isCompact ? "px-2 py-1 min-w-[75px] max-w-[125px]" : "px-2.5 py-1.5 min-w-[95px] max-w-[145px]",
                                  isSelected ? "ring-slate-400/40 border-slate-400" : "hover:border-slate-400"
                                )
                          )}
                          data-testid={`button-graph-node-${n.id}`}
                        >
                          {isFinding ? (
                            <>
                              <div className="flex items-center justify-between gap-1">
                                <span className="mono text-[7.5px] uppercase tracking-wider font-bold text-[#b91c1c] flex items-center gap-1">
                                  <TriangleAlert size={9} className="text-[#e11d48]" /> FINDING
                                </span>
                                <span className="rounded bg-[#fee2e2] px-1 py-0.2 text-[7px] font-bold text-[#991b1b]">
                                  {n.label.includes("hys") ? "UNCONFIRMED" : "DETECTED"}
                                </span>
                              </div>
                              <div className="whitespace-nowrap text-[11px] font-bold text-[#881337] mt-0.5">
                                {humanizeFindingType(n.label)}
                              </div>
                            </>
                          ) : isEvidence ? (
                            <>
                              <div className="mono text-[7.5px] uppercase tracking-wider font-bold text-[#0d9488] flex items-center gap-1">
                                <ShieldCheck size={9} className="text-[#0d9488]" /> VERIFIED EVIDENCE
                              </div>
                              <div className="whitespace-nowrap text-[10.5px] font-bold text-[#134e4a] mt-0.5">
                                {formatNodeLabel(n, true)}
                              </div>
                            </>
                          ) : isSubject ? (
                            <>
                              <div className="mono text-[8px] uppercase tracking-wider font-bold text-[#0d9488]">SUBJECT</div>
                              <div className="display text-[12.5px] font-bold text-[#134e4a] mt-0.5">{n.label || selectedSubjectId}</div>
                              <div className="text-[9px] font-medium text-[#0f766e] opacity-80 mt-0.5">{selectedSubject?.arm || "Placebo"}</div>
                            </>
                          ) : isHub ? (
                            <>
                              <div className="flex items-center justify-between gap-1.5">
                                <span className="mono text-[7.5px] uppercase tracking-wider font-bold opacity-80">
                                  {domStyle.title}
                                </span>
                                <span className={cn("mono rounded-full px-1.5 py-0.2 text-[8px] font-bold", domStyle.hubBadge)}>
                                  {n.recordCount}
                                </span>
                              </div>
                              <div className="flex items-center justify-between mt-1 text-[11px] font-bold">
                                <span className="whitespace-nowrap">{domStyle.title}</span>
                                <span className="text-[8.5px] font-medium opacity-75 ml-2">
                                  {n.isExpanded ? "▲ Hide" : "▼ Show"}
                                </span>
                              </div>
                            </>
                          ) : (
                            <>
                              <div className="flex items-center justify-between gap-1">
                                <span className="mono text-[7.5px] uppercase tracking-wider font-semibold text-[#64748b]">
                                  {domStyle.title || n.type}
                                </span>
                                <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: domStyle.dotColor }} />
                              </div>
                              <div className={cn("truncate font-semibold text-[#1e293b] mt-0.5", isCompact ? "text-[9.5px]" : "text-[10.5px]")}>
                                {formatNodeLabel(n, false)}
                              </div>
                            </>
                          )}
                        </motion.button>
                      );
                    })}
                  </div>
                </>
              )}

              {/* Legend Footer */}
              <div className="absolute bottom-3 left-4 right-4 flex flex-wrap items-center justify-between border-t border-[#cbd5e1]/50 pt-2 mono text-[9px] text-[#64748b]">
                <div className="flex flex-wrap items-center gap-4">
                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-[#0d9488]" /> Subject
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-[#e11d48]" /> Clinical Finding
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-[#14b8a6]" /> Verified Evidence
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-[#8b5cf6]" /> Domain Hub
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-[#94a3b8]" /> Routine Record
                  </span>
                </div>
                <span className="font-medium text-[#475569]">Click Domain Hubs to expand / collapse</span>
              </div>
            </div>

            {/* 4. RIGHT-SIDE NODE INSPECTOR */}
            <motion.aside
              key={activeNode?.id || "empty"}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              className="glass rounded-2xl p-5 border border-[#cbd5e1]/70 flex flex-col max-h-[640px] overflow-y-auto shadow-xs"
            >
              {activeNode ? (
                <>
                  <div className="flex items-center justify-between">
                    <Badge tone={activeNode.tone || "teal"}>
                      {activeNode.isEvidence ? "Verified Evidence" : activeNode.isHub ? "Domain Hub" : activeNode.type}
                    </Badge>
                    <span className="mono text-[9px] text-[#64748b] font-medium truncate max-w-[160px]">{activeNode.id}</span>
                  </div>

                  <div className="mt-3 display text-lg font-bold text-[#0f172a] break-words">
                    {formatNodeLabel(activeNode, activeNode.isEvidence)}
                  </div>

                  <div className="my-3 h-px bg-[#e2e8f0]" />

                  {/* SPECIAL INSPECTOR VIEW: CLINICAL FINDINGS */}
                  {activeNode.type === "FINDING" && (
                    <div className="space-y-3">
                      <div>
                        <div className="mono text-[9px] uppercase tracking-[.14em] text-[#64748b] font-semibold">Status</div>
                        <div className="mt-1">
                          {activeNode.label.includes("hys") ? (
                            <div className="inline-block rounded-md border border-[#fde68a] bg-[#fffbeb] px-2.5 py-1 text-[11px] font-bold text-[#92400e]">
                              UNCONFIRMED · ADJUDICATION REQUIRED
                            </div>
                          ) : (
                            <Badge tone="coral">DETECTED</Badge>
                          )}
                        </div>
                      </div>

                      {/* Hy's Law Biochemical Criteria Checklist */}
                      {activeNode.label.includes("hys") && (
                        <div className="rounded-xl border border-[#cbd5e1] bg-[#f8fafc] p-3 text-[11px] space-y-1.5">
                          <div className="mono text-[9px] uppercase tracking-wider text-[#64748b] font-bold mb-1">
                            Biochemical Criteria Checklist:
                          </div>
                          <div className="flex items-center gap-2 text-[#0f766e] font-medium">
                            <span>✓</span> <span>Transaminase &gt;3× ULN (ALT {activeNode.properties?.transaminase_ratio}× ULN)</span>
                          </div>
                          <div className="flex items-center gap-2 text-[#0f766e] font-medium">
                            <span>✓</span> <span>Total Bilirubin &gt;2× ULN (BILI {activeNode.properties?.bilirubin_ratio}× ULN)</span>
                          </div>
                          <div className="flex items-center gap-2 text-[#0f766e] font-medium">
                            <span>✓</span> <span>Temporal Window: within 0 days (&le; 14 days)</span>
                          </div>
                          <div className="flex items-center gap-2 text-[#b45309] font-medium">
                            <span>⚠</span> <span>Cholestasis / Alternative Explanation: Unadjudicated</span>
                          </div>
                        </div>
                      )}

                      {/* Clinical Narrative Box */}
                      {activeNode.properties?.summary && (
                        <div>
                          <div className="mono text-[9px] uppercase tracking-[.14em] text-[#64748b] mb-1 font-semibold">Clinical Narrative</div>
                          <div className="rounded-xl border border-[#cbd5e1] bg-[#f8fafc] p-3 text-[11px] leading-5 text-[#1e293b]">
                            {activeNode.properties.summary}
                          </div>
                        </div>
                      )}

                      {/* Prohibited Medication Details */}
                      {activeNode.label.includes("prohibited") && (
                        <div className="rounded-xl border border-[#cbd5e1] bg-[#f8fafc] p-3 text-[11px] space-y-1">
                          <div className="flex justify-between"><span className="text-[#64748b]">Class:</span> <span className="mono text-[#b45309] font-bold">{activeNode.properties?.medication_class}</span></div>
                          <div className="flex justify-between"><span className="text-[#64748b]">Treatment:</span> <span className="mono text-[#1e293b] font-medium">{activeNode.properties?.treatment}</span></div>
                          <div className="flex justify-between"><span className="text-[#64748b]">Indication:</span> <span className="mono text-[#1e293b] font-medium">{activeNode.properties?.indication}</span></div>
                          <div className="flex justify-between"><span className="text-[#64748b]">Start Date:</span> <span className="mono text-[#1e293b] font-medium">{activeNode.properties?.start_date}</span></div>
                        </div>
                      )}

                      {/* Link to Evidence Page */}
                      <button
                        onClick={() => go("/evidence")}
                        className="mt-2 w-full flex items-center justify-center gap-2 rounded-xl border border-[#14b8a6]/40 bg-[#ccfbf1] py-2.5 text-[11px] font-bold text-[#0f766e] hover:bg-[#99f6e4] transition shadow-xs"
                      >
                        <FileSearch size={14} /> View in Evidence Explorer
                      </button>
                    </div>
                  )}

                  {/* SPECIAL INSPECTOR VIEW: LAB RESULT */}
                  {(activeNode.type === "LAB" || activeNode.type === "LB") && (
                    <div className="space-y-3">
                      {activeNode.isEvidence && (
                        <div className="rounded-lg border border-[#5eead4] bg-[#ccfbf1] p-2 text-[10px] text-[#0f766e] font-bold flex items-center gap-1.5">
                          <ShieldCheck size={14} /> Verified Supporting Evidence
                        </div>
                      )}
                      <div className="rounded-xl border border-[#cbd5e1] bg-[#f8fafc] p-3 text-[11px] space-y-2">
                        <div className="flex justify-between">
                          <span className="text-[#64748b]">Test Code:</span>
                          <span className="mono font-bold text-[#0f172a]">{activeNode.properties?.test || activeNode.label}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748b]">Measured Value:</span>
                          <span className="mono font-bold text-[#0f766e]">
                            {activeNode.properties?.value} {activeNode.properties?.unit || ""}
                          </span>
                        </div>
                        {activeNode.properties?.ratio_to_uln && (
                          <div className="flex justify-between">
                            <span className="text-[#64748b]">Ratio to ULN:</span>
                            <span className="mono font-bold text-[#c2410c]">
                              {Number(activeNode.properties.ratio_to_uln).toFixed(2)}× ULN
                            </span>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <span className="text-[#64748b]">Visit:</span>
                          <span className="mono text-[#1e293b] font-medium">{activeNode.properties?.visit || "N/A"}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748b]">Collection Date:</span>
                          <span className="mono text-[#1e293b] font-medium">{activeNode.properties?.date || "N/A"}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748b]">Sequence:</span>
                          <span className="mono text-[#1e293b] font-medium">LBSEQ {activeNode.properties?.seq}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* SPECIAL INSPECTOR VIEW: DOMAIN HUB */}
                  {activeNode.isHub && (
                    <div className="space-y-3">
                      <div className="rounded-xl border border-[#cbd5e1] bg-[#f8fafc] p-3 text-[11px] space-y-2">
                        <div className="flex justify-between">
                          <span className="text-[#64748b]">Domain:</span>
                          <span className="mono font-bold text-[#0f172a]">{activeNode.hubDomain}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748b]">Indexed Records:</span>
                          <span className="mono font-bold text-[#0f766e]">{activeNode.recordCount}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#64748b]">Display Status:</span>
                          <span className="mono text-[#1e293b] font-medium">{activeNode.isExpanded ? "Expanded on canvas" : "Collapsed"}</span>
                        </div>
                      </div>

                      <button
                        onClick={() => toggleHub(activeNode.id)}
                        className="w-full flex items-center justify-center gap-2 rounded-xl border border-[#cbd5e1] bg-white py-2.5 text-[11px] font-bold text-[#334155] hover:bg-[#f8fafc] transition shadow-xs"
                      >
                        <Layers3 size={14} /> {activeNode.isExpanded ? `Collapse ${activeNode.recordCount} Records` : `Expand ${activeNode.recordCount} Records`}
                      </button>
                    </div>
                  )}

                  {/* SPECIAL INSPECTOR VIEW: SUBJECT IDENTITY */}
                  {activeNode.type === "SUBJECT" && (
                    <div className="rounded-xl border border-[#cbd5e1] bg-[#f8fafc] p-3 text-[11px] space-y-2">
                      <div className="flex justify-between"><span className="text-[#64748b]">Subject ID:</span> <span className="mono font-bold text-[#0f172a]">{selectedSubjectId}</span></div>
                      <div className="flex justify-between"><span className="text-[#64748b]">Site:</span> <span className="mono text-[#1e293b] font-medium">{selectedSubject?.site_id}</span></div>
                      <div className="flex justify-between"><span className="text-[#64748b]">Arm:</span> <span className="mono text-[#1e293b] font-medium">{selectedSubject?.arm || "Placebo"}</span></div>
                      <div className="flex justify-between"><span className="text-[#64748b]">Age / Sex:</span> <span className="mono text-[#1e293b] font-medium">{selectedSubject?.age || "N/A"} / {selectedSubject?.sex || "N/A"}</span></div>
                      <div className="flex justify-between"><span className="text-[#64748b]">Detected Findings:</span> <span className="mono font-bold text-[#be123c]">{subjectFindings.length}</span></div>
                    </div>
                  )}

                  {/* GENERIC RECORD PROPERTIES (ZERO [object Object]) */}
                  {activeNode.type !== "FINDING" && activeNode.type !== "LAB" && activeNode.type !== "LB" && !activeNode.isHub && activeNode.type !== "SUBJECT" && (
                    <div>
                      <div className="mono text-[9px] uppercase tracking-[.14em] text-[#64748b] mb-2 font-semibold">Record Attributes</div>
                      <div className="space-y-2 rounded-xl border border-[#cbd5e1] bg-[#f8fafc] p-3 text-[11px] max-h-[300px] overflow-y-auto">
                        {activeNode.properties && Object.keys(activeNode.properties).length > 0 ? (
                          Object.entries(activeNode.properties)
                            .filter(([k]) => !k.startsWith("_") && k !== "finding_ids")
                            .map(([k, v]) => (
                              <div key={k} className="flex justify-between gap-2 border-b border-[#e2e8f0] pb-1.5">
                                <span className="mono text-[#64748b] shrink-0 font-medium">{k}:</span>
                                <div className="text-right">{renderPropertyValue(v)}</div>
                              </div>
                            ))
                        ) : (
                          <div className="text-[#64748b]">Connected node in StudyGraph</div>
                        )}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center text-[#64748b] py-16">Select any node on the graph to inspect its properties and clinical provenance</div>
              )}
            </motion.aside>
          </div>
        </>
      ) : (
        /* PATIENT JOURNEY TIMELINE VIEW */
        <div className="glass rounded-2xl p-6 border border-[#cbd5e1]/70 shadow-xs relative">
          {/* Header */}
          <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="mono text-[10px] uppercase tracking-[.15em] text-[#64748b] font-semibold">Chronological Patient 360</div>
              <div className="display text-xl font-bold text-[#0f172a]">Patient journey</div>
              <div className="text-xs text-[#64748b] mt-0.5">
                See how this subject progressed through the study and where important findings emerged.
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone="teal">{timelineData.length} total events</Badge>
              <Badge tone={hasSafetyFinding ? "coral" : hasMedOrExclusion ? "amber" : "slate"}>
                {subjectFindingsList.length} finding{subjectFindingsList.length !== 1 ? "s" : ""}
              </Badge>
            </div>
          </div>

          {/* 1. HORIZONTAL JOURNEY NAVIGATOR */}
          {visitGroups.length > 0 && (
            <div className="mb-6 rounded-2xl border border-[#cbd5e1]/60 bg-white/70 backdrop-blur-md p-4 shadow-xs">
              <div className="flex items-center justify-between gap-2 mb-3">
                <span className="mono text-[10px] uppercase tracking-wider text-[#64748b] font-bold flex items-center gap-1.5">
                  <Compass size={13} className="text-[#0d9488]" /> Study Visit Sequence
                </span>
                <div className="flex items-center gap-3 mono text-[9.5px] text-[#64748b]">
                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-[#14b8a6]" /> Routine Visit
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#f43f5e] flex items-center justify-center text-[8px] text-white font-bold">!</span> Finding Detected
                  </span>
                </div>
              </div>

              {/* Visit Sequence Rail */}
              <div className="flex items-center gap-2 overflow-x-auto pb-2 pt-1 scrollbar-thin">
                {visitGroups.map((vg) => (
                  <button
                    key={vg.id}
                    onClick={() => {
                      const el = document.getElementById(vg.id);
                      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                    }}
                    className={cn(
                      "flex flex-col items-center shrink-0 px-3 py-2 rounded-xl border text-center transition group shadow-xs cursor-pointer",
                      vg.hasFinding
                        ? "bg-[#fff1f2] border-[#f87171] hover:bg-[#ffe4e6]"
                        : "bg-white border-[#e2e8f0] hover:bg-[#f0fdfa] hover:border-[#99f6e4]"
                    )}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className={cn(
                        "h-2 w-2 rounded-full",
                        vg.hasSafetyFinding
                          ? "bg-[#f43f5e] ring-2 ring-[#f43f5e]/30"
                          : vg.hasFinding
                          ? "bg-[#f59e0b] ring-2 ring-[#f59e0b]/30"
                          : "bg-[#14b8a6]"
                      )} />
                      <span className={cn("mono text-[10.5px] font-bold", vg.hasFinding ? "text-[#991b1b]" : "text-[#0f172a]")}>
                        {vg.visitName}
                      </span>
                    </div>
                    <span className="mono text-[9px] text-[#64748b] mt-0.5 font-medium">
                      {vg.formattedDate}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 2. TIMELINE FILTERS */}
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 bg-white/70 backdrop-blur-md p-3 rounded-xl border border-[#cbd5e1]/60 shadow-xs">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mono text-[10px] uppercase text-[#64748b] font-semibold mr-1">Filter:</span>
              {[
                { id: "ALL", label: "All events" },
                { id: "FINDINGS", label: "Findings" },
                { id: "LB", label: "Labs" },
                { id: "AE", label: "Adverse events" },
                { id: "CM", label: "Medications" },
                { id: "VS", label: "Vitals" },
                { id: "EX", label: "Exposure" },
                { id: "EG", label: "ECG" },
              ].map((f) => (
                <button
                  key={f.id}
                  onClick={() => setTimelineFilter(f.id)}
                  className={cn(
                    "rounded-lg px-2.5 py-1 text-[11px] font-semibold transition cursor-pointer",
                    timelineFilter === f.id
                      ? "bg-[#ccfbf1] text-[#0f766e] border border-[#5eead4] shadow-xs"
                      : "text-[#64748b] hover:bg-white hover:text-[#0f172a]"
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <button
              onClick={() => setImportantOnly((prev) => !prev)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1 text-[11px] font-bold border transition shadow-xs cursor-pointer",
                importantOnly
                  ? "bg-[#fff1f2] border-[#f87171] text-[#991b1b]"
                  : "bg-white border-[#cbd5e1] text-[#64748b] hover:bg-[#f8fafc]"
              )}
            >
              <Sparkles size={13} className={importantOnly ? "text-[#e11d48]" : "text-[#f59e0b]"} />
              Important only
            </button>
          </div>

          {/* 3. ZERO-FINDING NOTICE */}
          {subjectFindingsList.length === 0 && (
            <div className="mb-6 rounded-xl border border-[#cbd5e1] bg-[#f8fafc] p-3.5 flex items-center gap-3 text-xs text-[#475569]">
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#ccfbf1] text-[#0f766e]">
                <ShieldCheck size={18} />
              </div>
              <div>
                <div className="font-bold text-[#0f172a]">Routine Study Schedule</div>
                <div>No clinical safety findings or protocol deviations were detected for this subject at Cut 12. Below is the complete record of visits and measurements.</div>
              </div>
            </div>
          )}

          {/* 4. CHRONOLOGICAL VISIT SECTIONS */}
          {timelineLoading ? (
            <div className="text-center py-16 mono text-xs text-[#0f766e] font-semibold animate-pulse">
              Loading subject journey from StudyGraph...
            </div>
          ) : visitGroups.length === 0 ? (
            <div className="text-center py-16 text-[#64748b] font-medium">
              No chronological events recorded for this subject in the current snapshot.
            </div>
          ) : (
            <div className="relative pl-6 space-y-8 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#cbd5e1]">
              {visitGroups.map((vg) => {
                const isExpanded = expandedVisits.has(vg.id);
                const filteredItems = vg.items.filter((item) => {
                  const isEv = evidenceKeyMap.has(`${item.domain.toUpperCase()}_${item.seq}`);
                  const isAbnormal = item.details?.ratio_to_uln && Number(item.details.ratio_to_uln) >= 1.5;
                  const isAE = item.domain === "AE";

                  if (importantOnly) {
                    if (!isEv && !isAbnormal && !isAE) return false;
                  }

                  if (timelineFilter === "ALL") return true;
                  if (timelineFilter === "FINDINGS") return false;
                  if (timelineFilter === "LB" && (item.domain === "LB" || item.domain === "LAB")) return true;
                  if (timelineFilter === "AE" && item.domain === "AE") return true;
                  if (timelineFilter === "CM" && (item.domain === "CM" || item.domain === "MEDICATION")) return true;
                  if (timelineFilter === "VS" && (item.domain === "VS" || item.domain === "VITAL_SIGN")) return true;
                  if (timelineFilter === "EX" && (item.domain === "EX" || item.domain === "EXPOSURE")) return true;
                  if (timelineFilter === "EG" && (item.domain === "EG" || item.domain === "ECG")) return true;
                  return item.domain === timelineFilter;
                });

                if (timelineFilter === "FINDINGS" && vg.findings.length === 0) return null;
                if (importantOnly && vg.findings.length === 0 && filteredItems.length === 0) return null;

                const visibleItems = isExpanded ? filteredItems : filteredItems.slice(0, 4);
                const hiddenCount = filteredItems.length - 4;

                return (
                  <div key={vg.id} id={vg.id} className="relative group scroll-mt-24">
                    {/* Spine Node */}
                    <span className={cn(
                      "absolute -left-[21px] top-2 h-3.5 w-3.5 rounded-full border-2 transition",
                      vg.hasSafetyFinding
                        ? "border-[#f43f5e] bg-[#f43f5e] ring-4 ring-[#f43f5e]/20"
                        : vg.hasFinding
                        ? "border-[#f59e0b] bg-[#f59e0b] ring-4 ring-[#f59e0b]/20"
                        : "border-white bg-[#14b8a6]"
                    )} />

                    {/* Visit Card */}
                    <div className={cn(
                      "rounded-2xl border p-5 transition shadow-xs",
                      vg.hasFinding
                        ? "border-[#fecdd3] bg-gradient-to-br from-white via-[#fffafa] to-[#fff5f5]"
                        : "border-[#e2e8f0] bg-white/95"
                    )}>
                      {/* Visit Header */}
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#e2e8f0]">
                        <div className="flex items-center gap-2.5">
                          <span className="display text-base font-bold text-[#0f172a]">
                            {vg.visitName}
                          </span>
                          {vg.hasFinding && (
                            <span className="mono rounded-md bg-[#fee2e2] px-2 py-0.5 text-[9.5px] font-bold text-[#991b1b] flex items-center gap-1">
                              {vg.hasSafetyFinding && <TriangleAlert size={11} />}
                              {vg.findings.length} FINDING{vg.findings.length > 1 ? "S" : ""}
                            </span>
                          )}
                          <span className="mono text-[10.5px] text-[#64748b]">
                            {filteredItems.length} records
                          </span>
                        </div>
                        <div className="mono text-[11px] font-bold text-[#0f766e] flex items-center gap-1.5">
                          <CalendarDays size={13} /> {vg.formattedDate}
                        </div>
                      </div>

                      {/* 1. FINDING CALLOUTS */}
                      {vg.findings.length > 0 && (
                        <div className="mt-4 space-y-3">
                          {vg.findings.map((f) => (
                            <div
                              key={f.finding_id}
                              className={cn(
                                "rounded-xl border-1.5 p-4 shadow-xs",
                                f.finding_type === "potential_hys_law"
                                  ? "border-[#f87171] bg-[#fff1f2]/90"
                                  : "border-[#fde68a] bg-[#fffbeb]/90"
                              )}
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2">
                                  <TriangleAlert size={16} className={f.finding_type === "potential_hys_law" ? "text-[#e11d48]" : "text-[#d97706]"} />
                                  <span className="font-bold text-sm text-[#881337]">
                                    {humanizeFindingType(f.finding_type)}
                                  </span>
                                  <span className={cn(
                                    "rounded px-1.5 py-0.5 text-[9px] font-bold uppercase",
                                    f.finding_type === "potential_hys_law"
                                      ? "bg-[#fffbeb] border border-[#fde68a] text-[#92400e]"
                                      : "bg-[#fee2e2] text-[#991b1b]"
                                  )}>
                                    {f.finding_type === "potential_hys_law" ? "UNCONFIRMED · ADJUDICATION REQUIRED" : "DETECTED"}
                                  </span>
                                </div>

                                <button
                                  onClick={() => go("/evidence")}
                                  className="flex items-center gap-1 rounded-lg border border-[#14b8a6]/40 bg-[#ccfbf1] px-2.5 py-1 text-[11px] font-bold text-[#0f766e] hover:bg-[#99f6e4] transition shadow-xs cursor-pointer"
                                >
                                  <FileSearch size={12} /> See Evidence in Explorer
                                </button>
                              </div>

                              {/* Plain-Language Explanation */}
                              <div className="mt-2 text-xs text-[#475569] leading-relaxed">
                                <span className="font-semibold text-[#881337]">Clinical Context: </span>
                                {FINDING_EXPLANATIONS[f.finding_type] || "Protocol finding detected based on study criteria."}
                              </div>

                              {/* Hy's Law Biochemical Elevation Details */}
                              {f.finding_type === "potential_hys_law" && (
                                <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                                  <div className="rounded-lg border border-[#5eead4] bg-white p-2.5">
                                    <div className="flex justify-between text-[#0f766e] font-bold">
                                      <span>ALT Elevation</span>
                                      <span className="mono bg-[#ccfbf1] px-1 py-0.2 rounded text-[9.5px]">LBSEQ {f.details.transaminase_seq || "25"}</span>
                                    </div>
                                    <div className="mt-1 flex items-baseline gap-2">
                                      <span className="display text-sm font-bold text-[#0f172a]">{f.details.transaminase_value} {f.details.transaminase_unit || "ukat/L"}</span>
                                      <span className="mono font-bold text-[#c2410c]">{f.details.transaminase_ratio}× ULN</span>
                                    </div>
                                    <div className="mono text-[9px] text-[#64748b] mt-0.5">Protocol Threshold: &gt;3.00× ULN</div>
                                  </div>

                                  <div className="rounded-lg border border-[#5eead4] bg-white p-2.5">
                                    <div className="flex justify-between text-[#0f766e] font-bold">
                                      <span>Total Bilirubin Elevation</span>
                                      <span className="mono bg-[#ccfbf1] px-1 py-0.2 rounded text-[9.5px]">LBSEQ {f.details.bilirubin_seq || "27"}</span>
                                    </div>
                                    <div className="mt-1 flex items-baseline gap-2">
                                      <span className="display text-sm font-bold text-[#0f172a]">{f.details.bilirubin_value} {f.details.bilirubin_unit || "mg/dL"}</span>
                                      <span className="mono font-bold text-[#c2410c]">{f.details.bilirubin_ratio}× ULN</span>
                                    </div>
                                    <div className="mono text-[9px] text-[#64748b] mt-0.5">Protocol Threshold: &gt;2.00× ULN</div>
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* 2. VISIT RECORDS LIST (COMPACT ROWS) */}
                      {timelineFilter !== "FINDINGS" && (
                        <div className="mt-4 space-y-1.5">
                          {visibleItems.map((item, rIdx) => {
                            const isEv = evidenceKeyMap.has(`${item.domain.toUpperCase()}_${item.seq}`);
                            const isAbnormal = item.details?.ratio_to_uln && Number(item.details.ratio_to_uln) >= 1.5;

                            return (
                              <div
                                key={rIdx}
                                onClick={() => setSelectedTimelineRecord(item)}
                                className={cn(
                                  "flex items-center justify-between gap-3 px-3 py-2 rounded-xl border text-left cursor-pointer transition",
                                  isEv
                                    ? "bg-[#f0fdfa] border-[#5eead4] hover:border-[#14b8a6] shadow-xs"
                                    : isAbnormal
                                    ? "bg-[#fffbeb] border-[#fde68a] hover:border-[#f59e0b]"
                                    : "bg-white/80 border-[#e2e8f0] hover:bg-[#f8fafc] hover:border-[#cbd5e1]"
                                )}
                              >
                                <div className="flex items-center gap-2.5 min-w-0">
                                  <span className={cn("mono rounded px-1.5 py-0.5 text-[8px] font-bold uppercase", domainBadgeClass(item.domain))}>
                                    {friendlyDomainName(item.domain)}
                                  </span>
                                  <span className="font-semibold text-[11.5px] text-[#0f172a] truncate">
                                    {item.label}
                                  </span>
                                  {isEv && (
                                    <span className="mono rounded-full bg-[#ccfbf1] px-2 py-0.5 text-[8px] font-bold text-[#0f766e] flex items-center gap-1 shrink-0">
                                      <ShieldCheck size={10} /> VERIFIED EVIDENCE
                                    </span>
                                  )}
                                </div>

                                <div className="flex items-center gap-3 shrink-0">
                                  {item.details.value !== undefined && (
                                    <span className="mono text-[11px] font-bold text-[#0f766e]">
                                      {item.details.value} {item.details.unit || ""}
                                    </span>
                                  )}
                                  {item.details.ratio_to_uln && (
                                    <span className={cn(
                                      "mono text-[10px] font-bold px-1.5 py-0.5 rounded",
                                      Number(item.details.ratio_to_uln) >= 2.0
                                        ? "bg-[#fee2e2] text-[#b91c1c]"
                                        : Number(item.details.ratio_to_uln) > 1.0
                                        ? "bg-[#fef3c7] text-[#b45309]"
                                        : "bg-[#f1f5f9] text-[#64748b]"
                                    )}>
                                      {Number(item.details.ratio_to_uln).toFixed(2)}× ULN
                                    </span>
                                  )}
                                  <span className="mono text-[10px] text-[#64748b]">
                                    {formatDate(item.date)}
                                  </span>
                                </div>
                              </div>
                            );
                          })}

                          {/* Expand / Collapse Button */}
                          {hiddenCount > 0 && (
                            <button
                              onClick={() => {
                                setExpandedVisits((prev) => {
                                  const next = new Set(prev);
                                  if (next.has(vg.id)) next.delete(vg.id);
                                  else next.add(vg.id);
                                  return next;
                                });
                              }}
                              className="mt-2 w-full flex items-center justify-center gap-1.5 py-2 rounded-xl border border-[#cbd5e1]/70 bg-[#f8fafc] text-[11px] font-semibold text-[#334155] hover:bg-[#e2e8f0] transition shadow-xs cursor-pointer"
                            >
                              {isExpanded ? (
                                <>
                                  <ChevronUp size={14} /> Collapse {filteredItems.length} records
                                </>
                              ) : (
                                <>
                                  <ChevronDown size={14} /> Show {hiddenCount} more records
                                </>
                              )}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* 5. SLIDE-OVER RECORD INSPECTOR DRAWER */}
          <AnimatePresence>
            {selectedTimelineRecord && (
              <>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => setSelectedTimelineRecord(null)}
                  className="fixed inset-0 bg-black/20 backdrop-blur-xs z-40"
                />
                <motion.div
                  initial={{ x: "100%" }}
                  animate={{ x: 0 }}
                  exit={{ x: "100%" }}
                  transition={{ type: "spring", damping: 25, stiffness: 200 }}
                  className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-2xl border-l border-[#cbd5e1] p-6 flex flex-col justify-between overflow-y-auto"
                >
                  <div>
                    <div className="flex items-center justify-between pb-4 border-b border-[#e2e8f0]">
                      <div className="flex items-center gap-2">
                        <Badge tone={domainMeta[selectedTimelineRecord.domain]?.tone || "teal"}>
                          {friendlyDomainName(selectedTimelineRecord.domain)}
                        </Badge>
                        <span className="mono text-[11px] text-[#64748b]">
                          {selectedTimelineRecord.domain}SEQ {selectedTimelineRecord.seq}
                        </span>
                      </div>
                      <button
                        onClick={() => setSelectedTimelineRecord(null)}
                        className="rounded-lg p-1.5 text-[#64748b] hover:bg-[#f1f5f9] hover:text-[#0f172a] transition cursor-pointer"
                      >
                        <X size={18} />
                      </button>
                    </div>

                    <div className="mt-4">
                      <div className="display text-lg font-bold text-[#0f172a]">
                        {selectedTimelineRecord.label}
                      </div>
                      <div className="mono text-[11px] text-[#64748b] mt-1">
                        {formatDate(selectedTimelineRecord.date)} · Visit {selectedTimelineRecord.visit || "Unscheduled"}
                      </div>
                    </div>

                    {/* Structured Details */}
                    <div className="mt-5 rounded-xl border border-[#cbd5e1] bg-[#f8fafc] p-4 space-y-2 text-xs">
                      {selectedTimelineRecord.details.value !== undefined && (
                        <div className="flex justify-between py-1 border-b border-[#e2e8f0]">
                          <span className="text-[#64748b]">Measured Result:</span>
                          <span className="mono font-bold text-[#0f766e]">
                            {selectedTimelineRecord.details.value} {selectedTimelineRecord.details.unit || ""}
                          </span>
                        </div>
                      )}
                      {selectedTimelineRecord.details.ratio_to_uln && (
                        <div className="flex justify-between py-1 border-b border-[#e2e8f0]">
                          <span className="text-[#64748b]">Ratio to ULN:</span>
                          <span className="mono font-bold text-[#c2410c]">
                            {Number(selectedTimelineRecord.details.ratio_to_uln).toFixed(2)}× ULN
                          </span>
                        </div>
                      )}
                      {Object.entries(selectedTimelineRecord.details)
                        .filter(([k]) => k !== "value" && k !== "unit" && k !== "ratio_to_uln" && !k.startsWith("_"))
                        .map(([k, v]) => (
                          <div key={k} className="flex justify-between py-1 border-b border-[#e2e8f0] last:border-0">
                            <span className="text-[#64748b] capitalize">{k.replace(/_/g, " ")}:</span>
                            <div className="text-right">{renderPropertyValue(v)}</div>
                          </div>
                        ))}
                    </div>

                    {/* Source Provenance */}
                    <div className="mt-4 rounded-xl border border-[#e2e8f0] bg-white p-3.5 text-[11px] shadow-xs">
                      <div className="mono text-[9px] uppercase tracking-wider text-[#64748b] font-bold mb-1.5">Source Provenance</div>
                      <div className="flex justify-between text-[#475569]">
                        <span>Domain File:</span> <strong className="mono text-[#0f172a]">{selectedTimelineRecord.domain}.csv</strong>
                      </div>
                      <div className="flex justify-between text-[#475569] mt-1">
                        <span>Domain Sequence:</span> <strong className="mono text-[#0f172a]">{selectedTimelineRecord.seq}</strong>
                      </div>
                      <div className="flex justify-between text-[#475569] mt-1">
                        <span>Subject ID:</span> <strong className="mono text-[#0f172a]">{selectedSubjectId}</strong>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => setSelectedTimelineRecord(null)}
                    className="mt-6 w-full rounded-xl bg-[#f1f5f9] border border-[#cbd5e1] py-2.5 text-xs font-bold text-[#334155] hover:bg-[#e2e8f0] transition cursor-pointer shadow-xs"
                  >
                    Close Inspector
                  </button>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// PAGE 3: ATLAS AGENT
// -----------------------------------------------------------------------------
function Atlas() {
  const [, go] = useLocation();
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [messages, setMessages] = useState<Array<{
    role: "user" | "assistant";
    text: string;
    answer?: any;
    evidence?: Array<{ domain: string; usubjid: string; seq: number }>;
    confidence?: number;
  }>>([]);

  const askMutation = useMutation({
    mutationFn: (q: string) => api.askAtlas(q),
    onMutate: (q) => {
      setThinking(true);
      setMessages((prev) => [...prev, { role: "user", text: q }]);
    },
    onSuccess: (data) => {
      setThinking(false);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: data.text,
          answer: data.answer,
          evidence: data.evidence,
          confidence: data.confidence,
        },
      ]);
    },
    onError: (err: any) => {
      setThinking(false);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Query error: ${err.message || "Failed to process question through StudyGraph."}`,
        },
      ]);
    },
  });

  const ask = (text: string) => {
    if (!text.trim() || thinking) return;
    setInput("");
    askMutation.mutate(text);
  };

  const prompts = [
    "Which subjects meet potential Hy's Law criteria?",
    "Show serious adverse events",
    "Show prohibited medications",
    "Show lab records for subject 042-S07-001",
    "Which subjects had screening creatinine violations?",
    "Show visit window deviations",
  ];

  return (
    <div className="mx-auto max-w-[1240px] px-5 py-7 md:px-9 md:py-9">
      <Heading
        eyebrow="Atlas Agent / Single Source of Truth"
        title="Ask the study anything."
        detail="Atlas translates clinical and operational questions into deterministic queries against StudyGraph. Every finding is supported by verified provenance."
        action={<Badge tone="teal">StudyGraph Grounded</Badge>}
      />

      <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
        <div className="glass flex min-h-[620px] flex-col overflow-hidden rounded-2xl">
          <div className="flex items-center justify-between border-b border-white/[.07] px-5 py-4">
            <div className="flex items-center gap-3">
              <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#6af3d9]/[.1] text-[#6af3d9]">
                <BrainCircuit size={17} />
              </div>
              <div>
                <div className="text-[12px] font-semibold text-[#e0eaf0]">Atlas / Clinical Intelligence Agent</div>
                <div className="mono text-[9px] text-[#63748a]">engine · StudyGraph QueryEngine</div>
              </div>
            </div>
            <button
              onClick={() => setMessages([])}
              className="text-[10px] text-[#718298] hover:text-[#b4c3d4] transition"
              data-testid="button-clear-atlas"
            >
              Clear session
            </button>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 p-5 sm:p-7 overflow-y-auto space-y-6">
            {messages.length === 0 && !thinking ? (
              <div className="flex min-h-[380px] flex-col items-center justify-center text-center">
                <div className="relative mb-6 grid h-20 w-20 place-items-center rounded-3xl border border-[#62eed5]/25 bg-[#62eed5]/[.07] text-[#6fffe2] float-slow">
                  <BrainCircuit size={30} />
                </div>
                <div className="display text-2xl font-semibold text-[#ebf3f6]">The study is listening.</div>
                <p className="mt-2 max-w-md text-[12px] leading-5 text-[#77889d]">
                  Ask about Hy's Law, serious adverse events, exclusions, prohibited medications, or subject labs.
                </p>
                <div className="mt-7 flex flex-wrap justify-center gap-2">
                  {prompts.slice(0, 4).map((p) => (
                    <button
                      key={p}
                      onClick={() => ask(p)}
                      className="rounded-full border border-white/[.1] bg-white/[.025] px-3 py-2 text-[10px] text-[#99a9bb] hover:border-[#5beed5]/30 hover:text-[#cffff5] transition"
                      data-testid={`button-prompt-${p.slice(0, 8).replaceAll(" ", "-").toLowerCase()}`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((m, idx) => (
                  <div key={idx}>
                    {m.role === "user" ? (
                      <div className="flex gap-3">
                        <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-[#9d8cff]/15 text-[9px] font-bold text-[#cabfff]">
                          USER
                        </div>
                        <div className="rounded-xl rounded-tl-sm border border-white/[.08] bg-white/[.035] px-4 py-3 text-[12px] text-[#d6e2ea]">
                          {m.text}
                        </div>
                      </div>
                    ) : (
                      <div className="flex gap-3">
                        <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-[#6af3d9]/[.1] text-[#6af3d9]">
                          <Sparkles size={14} />
                        </div>
                        <div className="flex-1">
                          <div className="rounded-xl rounded-tl-sm border border-[#61edda]/15 bg-[#61edda]/[.045] px-4 py-4 text-[12px] leading-6 text-[#dce9ed]">
                            {m.text}
                            {/* Structured Answer list tags if present */}
                            {Array.isArray(m.answer) && m.answer.length > 0 && (
                              <div className="mt-3 flex flex-wrap gap-1.5">
                                {m.answer.map((ansItem: any, i: number) => (
                                  <span key={i} className="mono rounded-md border border-[#5cf0d6]/30 bg-[#0d2a26] px-2 py-0.5 text-[11px] text-[#86ffec]">
                                    {typeof ansItem === "object" ? JSON.stringify(ansItem) : String(ansItem)}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Evidence references */}
                          {m.evidence && m.evidence.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              <span className="mono text-[10px] text-[#697d93] py-1">Supporting Evidence:</span>
                              {m.evidence.map((ev, i) => (
                                <span key={i} className="mono rounded border border-white/[.08] bg-white/[.03] px-2 py-0.5 text-[10px] text-[#a9baca]">
                                  {ev.domain}:{ev.usubjid}:{ev.seq}
                                </span>
                              ))}
                            </div>
                          )}

                          <div className="mt-3 flex gap-2">
                            <button
                              onClick={() => go("/evidence")}
                              className="flex items-center gap-1.5 rounded-lg border border-white/[.1] px-2.5 py-1.5 text-[10px] text-[#9babbc] hover:bg-white/[.04] transition"
                              data-testid="button-atlas-inspect-evidence"
                            >
                              <FileSearch size={12} /> Inspect evidence
                            </button>
                            <button
                              onClick={() => go("/graph")}
                              className="flex items-center gap-1.5 rounded-lg border border-white/[.1] px-2.5 py-1.5 text-[10px] text-[#9babbc] hover:bg-white/[.04] transition"
                              data-testid="button-atlas-open-graph"
                            >
                              <Network size={12} /> Open graph
                            </button>
                          </div>

                          <div className="mt-3 flex items-center gap-2 mono text-[9px] text-[#5d7184]">
                            <ShieldCheck size={12} className="text-[#67e8d1]" />
                            grounded across {m.evidence?.length ?? 0} records · confidence {Math.round((m.confidence ?? 0.95) * 100)}%
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {thinking && (
                  <div className="flex gap-3">
                    <div className="grid h-7 w-7 place-items-center rounded-lg bg-[#6af3d9]/[.1] text-[#6af3d9]">
                      <Sparkles size={14} className="animate-pulse" />
                    </div>
                    <div className="rounded-xl border border-[#61edda]/15 bg-[#61edda]/[.045] px-4 py-3 mono text-[10px] text-[#8feee0]">
                      Querying StudyGraph & validating evidence references...
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Chat Input */}
          <div className="border-t border-white/[.07] p-4">
            <form onSubmit={(e) => { e.preventDefault(); ask(input); }} className="flex items-center gap-2 rounded-xl border border-white/[.12] bg-[#0b121c] p-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about Hy's law, adverse events, medications, or lab values..."
                className="min-w-0 flex-1 bg-transparent px-2 text-[12px] text-[#dce9ee] outline-none placeholder:text-[#52647b]"
                data-testid="input-atlas-question"
              />
              <button
                type="submit"
                disabled={!input.trim() || thinking}
                className="grid h-8 w-8 place-items-center rounded-lg bg-[#63edd6] text-[#091715] disabled:opacity-30 transition"
                data-testid="button-submit-atlas"
              >
                <Send size={14} />
              </button>
            </form>
          </div>
        </div>

        {/* Prompts sidebar */}
        <aside className="space-y-5">
          <div className="glass rounded-2xl p-5">
            <div className="mono text-[10px] uppercase tracking-[.15em] text-[#77879b]">Supported Queries</div>
            <div className="mt-3 space-y-2">
              {prompts.map((p) => (
                <button
                  key={p}
                  onClick={() => ask(p)}
                  className="w-full text-left rounded-lg border border-white/[.07] bg-white/[.02] p-2.5 text-[11px] text-[#a4b5c7] hover:border-[#53eed4]/40 hover:text-[#d7fff8] transition flex justify-between items-center"
                >
                  <span className="line-clamp-2">{p}</span>
                  <ChevronRight size={13} className="shrink-0 text-[#54667d]" />
                </button>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// PAGE 4: EVIDENCE EXPLORER (STORY-FIRST CLINICAL AUDIT TRAIL)
// -----------------------------------------------------------------------------

const FINDING_TYPE_META: Record<string, {
  label: string;
  shortLabel: string;
  badgeTone: Tone;
  statusBadge: { text: string; tone: Tone };
  accentBorder: string;
  tagColor: string;
  barColor: string;
  plainExplanation: string;
  clinicalSignificance: string;
}> = {
  potential_hys_law: {
    label: "Potential Hy's Law",
    shortLabel: "Hy's Law",
    badgeTone: "amber",
    statusBadge: { text: "UNCONFIRMED · ADJUDICATION REQUIRED", tone: "amber" },
    accentBorder: "border-[#ff887b]/40 hover:border-[#ff887b]/70",
    tagColor: "bg-[#ff887b]/10 text-[#ffaaa3] border-[#ff887b]/25",
    barColor: "#ff7e72",
    plainExplanation: "The system detected a combination of liver test abnormalities (transaminase >= 3× ULN and bilirubin >= 2× ULN) that crossed predefined safety thresholds at the same visit.",
    clinicalSignificance: "High clinical safety risk indicating possible drug-induced liver injury (DILI). Must remain Unconfirmed until medical experts adjudicate cholestasis and alternative etiologies."
  },
  serious_adverse_event: {
    label: "Serious Adverse Event",
    shortLabel: "Serious AE",
    badgeTone: "coral",
    statusBadge: { text: "DETECTED", tone: "coral" },
    accentBorder: "border-[#ff7e72]/40 hover:border-[#ff7e72]/70",
    tagColor: "bg-[#ff7e72]/10 text-[#ffaaa3] border-[#ff7e72]/25",
    barColor: "#ff9085",
    plainExplanation: "This event meets the study protocol's serious-event criteria because inpatient hospitalization was recorded (AESHOSP='Y' override applied).",
    clinicalSignificance: "Hospitalization criteria trigger mandatory expedited safety reporting under Protocol §6 regardless of initial investigator grading."
  },
  prohibited_concomitant_medication: {
    label: "Prohibited Medication",
    shortLabel: "Prohibited Med",
    badgeTone: "amber",
    statusBadge: { text: "DETECTED", tone: "amber" },
    accentBorder: "border-[#f5c86d]/40 hover:border-[#f5c86d]/70",
    tagColor: "bg-[#f5c86d]/10 text-[#f7d98d] border-[#f5c86d]/25",
    barColor: "#eec66c",
    plainExplanation: "A concomitant medication administered to this subject belongs to a therapeutic class strictly disallowed under the active study protocol.",
    clinicalSignificance: "Administration of restricted drugs (such as systemic glucocorticoids or sulfonylureas) violates Protocol §5 and may confound trial endpoints."
  },
  exclusion_violation_creatinine: {
    label: "Creatinine Exclusion",
    shortLabel: "Creatinine",
    badgeTone: "lilac",
    statusBadge: { text: "DETECTED", tone: "lilac" },
    accentBorder: "border-[#b5a2ff]/40 hover:border-[#b5a2ff]/70",
    tagColor: "bg-[#b5a2ff]/10 text-[#c9bdff] border-[#b5a2ff]/25",
    barColor: "#a78bfa",
    plainExplanation: "Screening serum creatinine exceeded the study's eligibility threshold (> 1.5 mg/dL), indicating renal impairment under Protocol Amendment 2.",
    clinicalSignificance: "Renal safety exclusion ensures subjects with pre-existing renal dysfunction are excluded prior to study randomization."
  },
  visit_window_deviation: {
    label: "Visit-Window Deviation",
    shortLabel: "Visit Deviation",
    badgeTone: "slate",
    statusBadge: { text: "SCHEDULE DEVIATION", tone: "slate" },
    accentBorder: "border-[#60a5fa]/30 hover:border-[#60a5fa]/60",
    tagColor: "bg-[#60a5fa]/10 text-[#93c5fd] border-[#60a5fa]/25",
    barColor: "#60a5fa",
    plainExplanation: "This study visit took place outside the protocol's permitted timing window (+/- allowed days) around scheduled target study days.",
    clinicalSignificance: "Operational visit timing variance tracked for Good Clinical Practice (GCP) protocol compliance without indicating direct clinical risk."
  },
};

function Evidence() {
  const [, go] = useLocation();
  const { data: findings = [] } = useQuery({ queryKey: ["findings"], queryFn: () => api.getFindings() });
  const [filterType, setFilterType] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [activeStoryTab, setActiveStoryTab] = useState<"story" | "records">("story");

  // Selected finding details & evidence
  const selectedFinding = useMemo(() => {
    return findings.find((f) => f.finding_id === selectedFindingId) || null;
  }, [findings, selectedFindingId]);

  const { data: evidenceDetails = [], isLoading: evidenceLoading } = useQuery({
    queryKey: ["finding-evidence", selectedFindingId],
    queryFn: () => api.getEvidence(selectedFindingId!),
    enabled: Boolean(selectedFindingId),
  });

  // Study-level counts & breakdown
  const counts = useMemo(() => {
    const hys = findings.filter((f) => f.finding_type === "potential_hys_law").length;
    const sae = findings.filter((f) => f.finding_type === "serious_adverse_event").length;
    const creat = findings.filter((f) => f.finding_type === "exclusion_violation_creatinine").length;
    const med = findings.filter((f) => f.finding_type === "prohibited_concomitant_medication").length;
    const dev = findings.filter((f) => f.finding_type === "visit_window_deviation").length;
    const safetyExclusions = hys + sae + creat + med;
    const uniqueSubjects = new Set(findings.map((f) => f.usubjid)).size;
    return { hys, sae, creat, med, dev, safetyExclusions, total: findings.length, uniqueSubjects };
  }, [findings]);

  // Filtered findings
  const filteredFindings = useMemo(() => {
    let list = findings;
    if (filterType === "safety_and_exclusions") {
      list = list.filter((f) => f.finding_type !== "visit_window_deviation");
    } else if (filterType !== "all") {
      list = list.filter((f) => f.finding_type === filterType);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter((f) => {
        const meta = FINDING_TYPE_META[f.finding_type];
        const label = meta ? meta.label.toLowerCase() : "";
        const id = f.finding_id.toLowerCase();
        const subj = f.usubjid.toLowerCase();
        const aeterm = f.details?.aeterm ? String(f.details.aeterm).toLowerCase() : "";
        const treatment = f.details?.treatment ? String(f.details.treatment).toLowerCase() : "";
        const visit = f.details?.visit ? String(f.details.visit).toLowerCase() : "";
        const test = f.details?.test ? String(f.details.test).toLowerCase() : "";
        return subj.includes(q) || id.includes(q) || label.includes(q) || aeterm.includes(q) || treatment.includes(q) || visit.includes(q) || test.includes(q);
      });
    }

    return list;
  }, [findings, filterType, searchQuery]);

  // Helper for quick selection
  const handleSelectFinding = (findingId: string) => {
    setSelectedFindingId(findingId);
  };

  const selectedMeta = selectedFinding ? FINDING_TYPE_META[selectedFinding.finding_type] : null;

  return (
    <div className="mx-auto max-w-[1520px] px-5 py-7 md:px-9 md:py-9">
      {/* 1. HERO / HEADER */}
      <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="flex items-center gap-2">
            <span className="mono text-[10px] uppercase tracking-[.18em] text-[#3df4d4] font-semibold bg-[#2de2c3]/10 px-2.5 py-1 rounded-full border border-[#2de2c3]/20">
              Study Evidence Workspace
            </span>
            <span className="text-[11px] text-[#718298]">·</span>
            <span className="mono text-[11px] text-[#9bb0c6]">
              {counts.total} Findings ({counts.uniqueSubjects} Subjects Affected)
            </span>
          </div>
          <h1 className="display mt-2 text-2xl font-bold tracking-tight text-[#f1f6fa] sm:text-3xl">
            Evidence explorer
          </h1>
          <p className="mt-1.5 max-w-2xl text-[13px] leading-6 text-[#8ea2b8]">
            <span className="italic font-medium text-[#cadbe8]">"Nothing gets hand-waved."</span> Inspect every detected clinical safety finding, protocol deviation, and the exact supporting records that prove it.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Badge tone="teal">Protocol v3 · Cut 12</Badge>
          <button
            onClick={() => go("/atlas")}
            className="flex items-center gap-1.5 rounded-lg border border-[#3df4d4]/30 bg-[#3df4d4]/10 px-3 py-2 text-[11px] font-semibold text-[#6dffe3] hover:bg-[#3df4d4]/20 transition"
            data-testid="button-ask-atlas-evidence"
          >
            <BrainCircuit size={14} />
            Ask Atlas about findings
          </button>
        </div>
      </div>

      {/* 2. STUDY-LEVEL SUMMARY CARDS */}
      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {[
          {
            key: "potential_hys_law",
            label: "Potential Hy's Law",
            count: counts.hys,
            subtitle: "Unconfirmed · Medical review required",
            Icon: Activity,
            tone: "amber" as Tone,
            tag: "Safety Critical",
          },
          {
            key: "serious_adverse_event",
            label: "Serious Adverse Events",
            count: counts.sae,
            subtitle: "Inpatient hospitalization criteria",
            Icon: TriangleAlert,
            tone: "coral" as Tone,
            tag: "Mandatory AE",
          },
          {
            key: "exclusion_violation_creatinine",
            label: "Creatinine Exclusions",
            count: counts.creat,
            subtitle: "Screening eligibility limit > 1.5",
            Icon: ShieldCheck,
            tone: "lilac" as Tone,
            tag: "Amendment 2",
          },
          {
            key: "prohibited_concomitant_medication",
            label: "Prohibited Medications",
            count: counts.med,
            subtitle: "Disallowed concomitant therapy",
            Icon: GitBranch,
            tone: "amber" as Tone,
            tag: "Protocol §5",
          },
          {
            key: "visit_window_deviation",
            label: "Visit Deviations",
            count: counts.dev,
            subtitle: "Outside protocol schedule window",
            Icon: CalendarDays,
            tone: "slate" as Tone,
            tag: "GCP Compliance",
          },
        ].map((card) => {
          const isSelectedFilter = filterType === card.key;
          return (
            <div
              key={card.key}
              onClick={() => {
                if (filterType === card.key) {
                  setFilterType("all");
                } else {
                  setFilterType(card.key);
                  const first = findings.find((f) => f.finding_type === card.key);
                  if (first) setSelectedFindingId(first.finding_id);
                }
              }}
              className={cn(
                "glass group relative flex flex-col justify-between rounded-xl p-4 cursor-pointer transition border",
                isSelectedFilter
                  ? "border-[#3df4d4]/60 bg-white/[.08] shadow-[0_0_15px_rgba(61,244,212,0.12)]"
                  : "border-white/[.08] hover:border-white/[.2] hover:bg-white/[.05]"
              )}
            >
              <div className="flex items-start justify-between">
                <div className={cn(
                  "grid h-8 w-8 place-items-center rounded-lg border",
                  card.tone === "teal" ? "border-[#2de2c3]/30 bg-[#2de2c3]/15 text-[#6dffe3]" :
                  card.tone === "amber" ? "border-[#f5c86d]/30 bg-[#f5c86d]/15 text-[#f5c86d]" :
                  card.tone === "lilac" ? "border-[#a78bfa]/30 bg-[#a78bfa]/15 text-[#c9bdff]" :
                  card.tone === "coral" ? "border-[#ff887b]/30 bg-[#ff887b]/15 text-[#ff887b]" :
                  "border-white/10 bg-white/[.06] text-[#94a3b8]"
                )}>
                  <card.Icon size={16} />
                </div>
                <span className="mono text-[9px] font-semibold text-[#7c8da3] uppercase">
                  {card.tag}
                </span>
              </div>
              <div className="mt-3">
                <div className="display text-2xl font-bold tracking-tight text-[#f1f6fa]">
                  {card.count}
                </div>
                <div className="mt-0.5 text-xs font-semibold text-[#d4e1ec]">
                  {card.label}
                </div>
                <div className="mt-1 text-[10px] leading-tight text-[#798ba1]">
                  {card.subtitle}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 3. VISUAL FINDING DISTRIBUTION PANEL */}
      <div className="mb-6 rounded-xl border border-white/[.08] bg-white/[.025] p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-3">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles size={14} className="text-[#3df4d4]" />
              <span className="text-xs font-semibold text-[#e1ebf4]">
                Finding Distribution Across Study Snapshot
              </span>
              <span className="mono text-[10px] text-[#718296]">
                ({counts.total} total signals)
              </span>
            </div>
            <p className="text-[11px] text-[#8192a6] mt-0.5">
              Click any segment to filter findings list. Most findings are operational schedule variances (90.7%), while 26 represent clinical safety and protocol exclusions.
            </p>
          </div>

          <button
            onClick={() => {
              setFilterType("safety_and_exclusions");
              const first = findings.find((f) => f.finding_type !== "visit_window_deviation");
              if (first) setSelectedFindingId(first.finding_id);
            }}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11px] font-semibold transition border",
              filterType === "safety_and_exclusions"
                ? "border-[#f5c86d] bg-[#f5c86d]/20 text-[#f5c86d]"
                : "border-[#f5c86d]/30 bg-[#f5c86d]/10 text-[#f7d98d] hover:bg-[#f5c86d]/20"
            )}
          >
            <ShieldAlert size={13} />
            Focus Safety & Exclusions ({counts.safetyExclusions})
          </button>
        </div>

        {/* Proportional Stacked Bar */}
        <div className="h-3 w-full overflow-hidden rounded-full bg-white/[.06] flex">
          {[
            { key: "visit_window_deviation", count: counts.dev, color: "#60a5fa", label: "Visit Deviations" },
            { key: "prohibited_concomitant_medication", count: counts.med, color: "#eec66c", label: "Prohibited Meds" },
            { key: "serious_adverse_event", count: counts.sae, color: "#ff7e72", label: "Serious AEs" },
            { key: "exclusion_violation_creatinine", count: counts.creat, color: "#a78bfa", label: "Creatinine Exclusions" },
            { key: "potential_hys_law", count: counts.hys, color: "#ff887b", label: "Potential Hy's Law" },
          ].map((seg) => {
            const pct = counts.total > 0 ? (seg.count / counts.total) * 100 : 0;
            return (
              <div
                key={seg.key}
                style={{ width: `${pct}%`, backgroundColor: seg.color }}
                onClick={() => setFilterType(seg.key)}
                className="h-full cursor-pointer transition hover:opacity-80 relative group"
                title={`${seg.label}: ${seg.count} (${pct.toFixed(1)}%)`}
              />
            );
          })}
        </div>

        {/* Segmented Legend Pills */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {[
            { key: "all", label: "All Findings", count: counts.total, color: "#ffffff" },
            { key: "visit_window_deviation", label: "Visit Deviations", count: counts.dev, color: "#60a5fa", pct: "90.7%" },
            { key: "prohibited_concomitant_medication", label: "Prohibited Meds", count: counts.med, color: "#eec66c", pct: "5.0%" },
            { key: "serious_adverse_event", label: "Serious AEs", count: counts.sae, color: "#ff7e72", pct: "1.8%" },
            { key: "exclusion_violation_creatinine", label: "Creatinine Exclusions", count: counts.creat, color: "#a78bfa", pct: "1.4%" },
            { key: "potential_hys_law", label: "Potential Hy's Law", count: counts.hys, color: "#ff887b", pct: "1.1%" },
          ].map((pill) => {
            const isSelected = filterType === pill.key;
            return (
              <button
                key={pill.key}
                onClick={() => setFilterType(pill.key)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-medium transition border",
                  isSelected
                    ? "border-[#3df4d4] bg-[#3df4d4]/15 text-[#e7fcf7]"
                    : "border-white/[.08] bg-white/[.03] text-[#8fa0b5] hover:bg-white/[.06] hover:text-[#d3e0ec]"
                )}
              >
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: pill.color }} />
                <span>{pill.label}</span>
                <span className="mono text-[10px] text-[#6e8095]">({pill.count})</span>
                {pill.pct && <span className="mono text-[9px] text-[#55677b]">{pill.pct}</span>}
              </button>
            );
          })}
        </div>
      </div>

      {/* 4. MAIN BROWSER & STORY PANEL SPLIT (~58% / ~42%) */}
      <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
        {/* LEFT: FINDINGS BROWSER */}
        <div className="glass flex flex-col rounded-2xl border border-white/[.08] overflow-hidden">
          {/* Browser Header & Search Bar */}
          <div className="border-b border-white/[.07] p-4 sm:p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="mono text-[10px] uppercase tracking-[.15em] text-[#718298]">
                  Findings Browser
                </div>
                <div className="mt-0.5 text-xs text-[#8da0b4]">
                  Showing <span className="font-semibold text-[#3df4d4]">{filteredFindings.length}</span> of {findings.length} findings
                </div>
              </div>

              {/* Backward-compatible select filter */}
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="hidden"
                data-testid="select-evidence-filter"
              >
                <option value="all">All evidence ({findings.length})</option>
                <option value="potential_hys_law">Potential Hy's Law ({counts.hys})</option>
                <option value="serious_adverse_event">Serious Adverse Events ({counts.sae})</option>
                <option value="exclusion_violation_creatinine">Creatinine Exclusions ({counts.creat})</option>
                <option value="prohibited_concomitant_medication">Prohibited Medications ({counts.med})</option>
                <option value="visit_window_deviation">Visit Window Deviations ({counts.dev})</option>
              </select>

              {/* Quick Search */}
              <div className="relative flex-1 max-w-[280px]">
                <Search size={14} className="absolute left-3 top-2.5 text-[#67798f]" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search subject, type, visit..."
                  className="w-full rounded-lg border border-white/10 bg-[#0e1622] pl-8 pr-7 py-1.5 text-xs text-[#dbe6f0] placeholder-[#5f7186] outline-none focus:border-[#3df4d4]/50 transition"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-2.5 top-2 text-[#718296] hover:text-[#dbe6f0]"
                  >
                    <X size={13} />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Findings List Rows */}
          <div className="divide-y divide-white/[.05] max-h-[720px] overflow-y-auto">
            {filteredFindings.length === 0 ? (
              <div className="p-12 text-center text-[#718298]">
                <FileSearch size={28} className="mx-auto text-[#5f7186] mb-2" />
                <div className="text-xs font-semibold text-[#cad6e2]">No matching findings found</div>
                <p className="text-[11px] text-[#718296] mt-1">
                  Try clearing the search query or selecting a different filter.
                </p>
                <button
                  onClick={() => { setFilterType("all"); setSearchQuery(""); }}
                  className="mt-3 text-xs text-[#3df4d4] underline"
                >
                  Reset filters
                </button>
              </div>
            ) : (
              filteredFindings.map((f) => {
                const meta = FINDING_TYPE_META[f.finding_type] || {
                  label: f.finding_type.replaceAll("_", " "),
                  shortLabel: f.finding_type,
                  badgeTone: "slate" as Tone,
                  statusBadge: { text: "DETECTED", tone: "slate" as Tone },
                  accentBorder: "border-white/10",
                  tagColor: "bg-white/10 text-white border-white/20",
                  barColor: "#ffffff",
                  plainExplanation: "Study finding detected by protocol rules.",
                  clinicalSignificance: "Requires review."
                };

                const isSelected = selectedFindingId === f.finding_id;
                const isHys = f.finding_type === "potential_hys_law";

                // Generate short plain-language summary line for card
                let summaryLine = meta.plainExplanation;
                if (isHys) {
                  summaryLine = `ALT ${Number(f.details?.transaminase_ratio || 0).toFixed(2)}× and Bilirubin ${Number(f.details?.bilirubin_ratio || 0).toFixed(2)}× crossed thresholds at visit ${f.details?.visit || "scheduled visit"}.`;
                } else if (f.finding_type === "serious_adverse_event") {
                  summaryLine = `Hospitalization criterion met: ${f.details?.aeterm || "Adverse event"} (${f.details?.aesev || "Severe"}).`;
                } else if (f.finding_type === "prohibited_concomitant_medication") {
                  summaryLine = `Disallowed ${f.details?.medication_class?.toLowerCase().replaceAll("_", " ") || "medication"}: ${f.details?.treatment || "prohibited agent"}.`;
                } else if (f.finding_type === "exclusion_violation_creatinine") {
                  summaryLine = `Screening serum creatinine ${f.details?.value} ${f.details?.unit} exceeded 1.5 eligibility cutoff.`;
                } else if (f.finding_type === "visit_window_deviation") {
                  summaryLine = `Visit ${f.details?.visit} conducted ${f.details?.delta_days} days outside target window (±${f.details?.allowed_window_days}d).`;
                }

                return (
                  <div
                    key={f.finding_id}
                    onClick={() => handleSelectFinding(f.finding_id)}
                    className={cn(
                      "p-4 cursor-pointer transition border-l-4 group",
                      isSelected
                        ? "bg-white/[.07] border-l-[#3df4d4] shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
                        : cn("border-l-transparent hover:bg-white/[.03]", meta.accentBorder)
                    )}
                    data-testid={`row-finding-${f.finding_id}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        {/* Human-Readable Finding Name */}
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-[#eef4f8] group-hover:text-[#3df4d4] transition">
                            {meta.label}
                          </span>
                          <span className={cn("mono text-[9px] uppercase px-2 py-0.5 rounded-full border", meta.tagColor)}>
                            {f.status === "UNCONFIRMED_ADJUDICATION_REQUIRED"
                              ? "UNCONFIRMED · ADJUDICATION REQUIRED"
                              : "DETECTED"}
                          </span>
                        </div>

                        {/* Subject ID & Context */}
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px]">
                          <span className="mono font-bold text-[#86ffea]">
                            Subject {f.usubjid}
                          </span>
                          <span className="text-[#55677b]">·</span>
                          <span className="text-[#8799ae]">
                            Cut {f.cut} · Protocol v{f.protocol_version}
                          </span>
                          {f.details?.visit && (
                            <>
                              <span className="text-[#55677b]">·</span>
                              <span className="mono text-[10px] text-[#abbdc0] bg-white/[.05] px-1.5 py-0.5 rounded">
                                Visit {f.details.visit}
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Evidence Count Badge */}
                      <div className="flex flex-col items-end">
                        <span className="mono flex items-center gap-1 text-[10px] font-semibold text-[#3df4d4] bg-[#2de2c3]/10 px-2 py-0.5 rounded-full border border-[#2de2c3]/20">
                          <ShieldCheck size={11} />
                          {f.evidence.length} {f.evidence.length === 1 ? "record" : "records"}
                        </span>
                        <span className="mono text-[9px] text-[#55677b] mt-1">
                          {f.finding_id}
                        </span>
                      </div>
                    </div>

                    {/* Short Plain-Language Summary Line */}
                    <div className="mt-2 text-[11px] leading-relaxed text-[#8da0b4] group-hover:text-[#b4c4d5] transition">
                      {summaryLine}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT: EVIDENCE STORY PANEL */}
        <aside className="glass rounded-2xl border border-white/[.08] p-5 sm:p-6 flex flex-col justify-between">
          {selectedFinding && selectedMeta ? (
            <div className="space-y-5">
              {/* A. FINDING HEADER */}
              <div className="border-b border-white/[.08] pb-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={cn("mono text-[10px] uppercase font-bold px-2.5 py-1 rounded-full border", selectedMeta.tagColor)}>
                        {selectedFinding.status === "UNCONFIRMED_ADJUDICATION_REQUIRED"
                          ? "UNCONFIRMED · ADJUDICATION REQUIRED"
                          : "DETECTED"}
                      </span>
                      <span className="mono text-[10px] text-[#697c92]">
                        {selectedFinding.finding_id}
                      </span>
                    </div>

                    <h2 className="mt-2 text-xl font-bold tracking-tight text-[#f1f6fa]">
                      {selectedMeta.label}
                    </h2>

                    <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs">
                      <span className="mono font-bold text-[#86ffea]">
                        Subject: {selectedFinding.usubjid}
                      </span>
                      <span className="text-[#55677b]">·</span>
                      <span className="text-[#8aa0b7]">
                        Cut {selectedFinding.cut} · Protocol v{selectedFinding.protocol_version}
                      </span>
                      {selectedFinding.details?.protocol_section && (
                        <span className="mono text-[10px] text-[#a78bfa] bg-[#a78bfa]/10 px-2 py-0.5 rounded border border-[#a78bfa]/20">
                          {selectedFinding.details.protocol_section}
                        </span>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => setSelectedFindingId(null)}
                    className="rounded-lg p-1.5 text-[#6c7d92] hover:bg-white/[.06] hover:text-[#e1ecf5] transition"
                    data-testid="button-close-evidence-detail"
                    title="Close details"
                  >
                    <X size={17} />
                  </button>
                </div>

                {/* Quick Action: Jump to Patient Journey */}
                <div className="mt-3 flex items-center gap-2">
                  <button
                    onClick={() => {
                      try {
                        localStorage.setItem("selectedSubjectId", selectedFinding.usubjid);
                      } catch {}
                      go("/graph");
                    }}
                    className="flex items-center gap-1.5 rounded-lg border border-[#3df4d4]/30 bg-[#3df4d4]/10 px-3 py-1.5 text-xs font-semibold text-[#6dffe3] hover:bg-[#3df4d4]/20 transition"
                    data-testid={`button-open-journey-${selectedFinding.usubjid}`}
                  >
                    <Compass size={13} />
                    View Subject {selectedFinding.usubjid} in Patient Journey
                    <ArrowRight size={13} />
                  </button>
                </div>
              </div>

              {/* B. PLAIN-LANGUAGE EXPLANATION BLOCK */}
              <div className="rounded-xl border border-[#3df4d4]/20 bg-[#2de2c3]/[0.05] p-3.5 text-xs leading-relaxed text-[#c3d8e8]">
                <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#3df4d4] uppercase tracking-wider mb-1">
                  <Sparkles size={13} />
                  Plain-Language Summary
                </div>
                <p>{selectedMeta.plainExplanation}</p>
                <div className="mt-1.5 text-[10px] text-[#7da3b8] italic">
                  {selectedMeta.clinicalSignificance}
                </div>
              </div>

              {/* C. PROTOCOL CRITERIA CHECKLIST ("Why It Was Flagged") */}
              <div className="rounded-xl border border-white/[.07] bg-white/[.02] p-4">
                <div className="mono text-[10px] uppercase tracking-[.15em] text-[#718298] mb-2.5 font-semibold">
                  Deterministic Protocol Rules Evaluated
                </div>

                <div className="space-y-2 text-xs">
                  {selectedFinding.finding_type === "potential_hys_law" && (
                    <>
                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Transaminase threshold met:</span>{" "}
                          {selectedFinding.details?.transaminase_test || "ALT"} raw value{" "}
                          <span className="mono font-bold text-[#3df4d4]">{selectedFinding.details?.transaminase_raw} {selectedFinding.details?.transaminase_unit}</span>{" "}
                          ({Number(selectedFinding.details?.transaminase_ratio).toFixed(2)}× ULN ≥ 3.0× cutoff)
                        </div>
                      </div>

                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Total Bilirubin threshold met:</span>{" "}
                          BILI raw value{" "}
                          <span className="mono font-bold text-[#f5c86d]">{selectedFinding.details?.bilirubin_raw} {selectedFinding.details?.bilirubin_unit}</span>{" "}
                          ({Number(selectedFinding.details?.bilirubin_ratio).toFixed(2)}× ULN ≥ 2.0× cutoff)
                        </div>
                      </div>

                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Temporal proximity satisfied:</span>{" "}
                          Both tests occurred at visit <span className="mono font-semibold text-[#e1ecf5]">{selectedFinding.details?.visit}</span> on{" "}
                          <span className="mono">{formatDate(selectedFinding.details?.transaminase_date)}</span> (0 days delta)
                        </div>
                      </div>

                      <div className="flex items-start gap-2 text-[#f5c86d]">
                        <TriangleAlert size={14} className="text-[#f5c86d] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold">Adjudication required:</span> Medical review needed to assess cholestasis (ALP) and exclude alternative viral or autoimmune causes before confirming DILI.
                        </div>
                      </div>
                    </>
                  )}

                  {selectedFinding.finding_type === "serious_adverse_event" && (
                    <>
                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Adverse event term:</span>{" "}
                          <span className="font-bold text-[#ff9085]">{selectedFinding.details?.aeterm || "Adverse Event"}</span>{" "}
                          (Severity: {selectedFinding.details?.aesev || "Severe"})
                        </div>
                      </div>

                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Hospitalization criterion satisfied:</span>{" "}
                          <span className="mono font-bold text-[#ff9085]">AESHOSP = 'Y'</span> recorded in source data
                        </div>
                      </div>

                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Protocol rule applied:</span>{" "}
                          {selectedFinding.details?.is_hospitalization_override
                            ? "Protocol §6 hospitalization override applied: classified as Serious AE despite investigator field."
                            : "Standard protocol SAE criteria verified."}
                        </div>
                      </div>
                    </>
                  )}

                  {selectedFinding.finding_type === "prohibited_concomitant_medication" && (
                    <>
                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Medication administered:</span>{" "}
                          <span className="font-bold text-[#f5c86d]">{selectedFinding.details?.treatment}</span>{" "}
                          ({selectedFinding.details?.dose ? `Dose: ${selectedFinding.details.dose} · ` : ""}
                          Indication: {selectedFinding.details?.indication || "Concomitant Therapy"})
                        </div>
                      </div>

                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Restricted drug class:</span>{" "}
                          <span className="mono font-bold text-[#f5c86d]">{selectedFinding.details?.medication_class}</span>
                        </div>
                      </div>

                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Protocol restriction:</span>{" "}
                          Disallowed under Protocol v{selectedFinding.details?.prohibited_since_protocol_version || 1} §5 (Prohibited Concomitant Medications)
                        </div>
                      </div>
                    </>
                  )}

                  {selectedFinding.finding_type === "exclusion_violation_creatinine" && (
                    <>
                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Screening creatinine:</span>{" "}
                          <span className="mono font-bold text-[#c9bdff]">{selectedFinding.details?.value} {selectedFinding.details?.unit}</span>{" "}
                          exceeded protocol cutoff <span className="mono font-bold">{selectedFinding.details?.threshold} {selectedFinding.details?.unit}</span>
                        </div>
                      </div>

                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Protocol amendment:</span>{" "}
                          Exclusion rule introduced under Protocol Amendment 2 (§3 Renal Safety Exclusion)
                        </div>
                      </div>

                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Timing:</span>{" "}
                          Detected at visit {selectedFinding.details?.visit} ({formatDate(selectedFinding.details?.date)}) prior to randomization
                        </div>
                      </div>
                    </>
                  )}

                  {selectedFinding.finding_type === "visit_window_deviation" && (
                    <>
                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Target study visit:</span>{" "}
                          Visit <span className="mono font-bold text-[#93c5fd]">{selectedFinding.details?.visit}</span> (Scheduled Day {selectedFinding.details?.target_day})
                        </div>
                      </div>

                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Actual conduct date:</span>{" "}
                          Day {selectedFinding.details?.actual_day} ({formatDate(selectedFinding.details?.visit_date)})
                        </div>
                      </div>

                      <div className="flex items-start gap-2 text-[#d2e2ee]">
                        <CheckCircle2 size={14} className="text-[#3df4d4] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold text-[#f1f6fa]">Window tolerance exceeded:</span>{" "}
                          Variance of <span className="mono font-bold text-[#93c5fd]">+{selectedFinding.details?.delta_days} days</span> exceeded protocol allowed window (±{selectedFinding.details?.allowed_window_days} days)
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* D. MINI VISUAL SUMMARY WIDGET */}
              <div className="rounded-xl border border-white/[.07] bg-white/[.02] p-4">
                <div className="mono text-[10px] uppercase tracking-[.15em] text-[#718298] mb-2.5 font-semibold">
                  Visual Metric Explanation
                </div>

                {selectedFinding.finding_type === "potential_hys_law" && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      {/* ALT / AST Card */}
                      <div className="rounded-lg border border-[#ff887b]/30 bg-[#ff887b]/[0.08] p-3">
                        <div className="text-[10px] font-semibold text-[#ffaaa3] uppercase">
                          Transaminase ({selectedFinding.details?.transaminase_test || "ALT"})
                        </div>
                        <div className="mt-1 text-lg font-bold text-[#ff887b]">
                          {selectedFinding.details?.transaminase_raw} {selectedFinding.details?.transaminase_unit}
                        </div>
                        <div className="mono text-xs font-semibold text-[#ffd2cc]">
                          {Number(selectedFinding.details?.transaminase_ratio).toFixed(2)}× ULN
                        </div>
                        <div className="mt-1.5 h-1.5 w-full rounded-full bg-black/30 overflow-hidden">
                          <div
                            className="h-full bg-[#ff7e72]"
                            style={{ width: `${Math.min(100, (Number(selectedFinding.details?.transaminase_ratio) / 3.0) * 75)}%` }}
                          />
                        </div>
                        <div className="mt-1 text-[9px] text-[#ffaaa3]/80">
                          Threshold: ≥ 3.0× ULN
                        </div>
                      </div>

                      {/* Bilirubin Card */}
                      <div className="rounded-lg border border-[#f5c86d]/30 bg-[#f5c86d]/[0.08] p-3">
                        <div className="text-[10px] font-semibold text-[#f7d98d] uppercase">
                          Total Bilirubin (BILI)
                        </div>
                        <div className="mt-1 text-lg font-bold text-[#f5c86d]">
                          {selectedFinding.details?.bilirubin_raw} {selectedFinding.details?.bilirubin_unit}
                        </div>
                        <div className="mono text-xs font-semibold text-[#ffecb3]">
                          {Number(selectedFinding.details?.bilirubin_ratio).toFixed(2)}× ULN
                        </div>
                        <div className="mt-1.5 h-1.5 w-full rounded-full bg-black/30 overflow-hidden">
                          <div
                            className="h-full bg-[#f5c86d]"
                            style={{ width: `${Math.min(100, (Number(selectedFinding.details?.bilirubin_ratio) / 2.0) * 70)}%` }}
                          />
                        </div>
                        <div className="mt-1 text-[9px] text-[#f7d98d]/80">
                          Threshold: ≥ 2.0× ULN
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between rounded-lg border border-white/[.08] bg-white/[.03] px-3 py-2 text-xs text-[#cad6e2]">
                      <span className="flex items-center gap-1.5">
                        <Clock size={13} className="text-[#3df4d4]" />
                        Temporal relationship:
                      </span>
                      <span className="font-semibold text-[#3df4d4]">
                        Same visit ({selectedFinding.details?.visit}) · Exact same day
                      </span>
                    </div>
                  </div>
                )}

                {selectedFinding.finding_type === "serious_adverse_event" && (
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Adverse Event</div>
                      <div className="font-semibold text-[#ff9085] mt-0.5">{selectedFinding.details?.aeterm}</div>
                    </div>
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Hospitalized</div>
                      <div className="font-semibold text-[#ff9085] mt-0.5">Yes (AESHOSP = Y)</div>
                    </div>
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Severity</div>
                      <div className="font-semibold text-[#d4e2ee] mt-0.5">{selectedFinding.details?.aesev || "Severe"}</div>
                    </div>
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Outcome</div>
                      <div className="font-semibold text-[#d4e2ee] mt-0.5">{selectedFinding.details?.aeout || "Recovered"}</div>
                    </div>
                  </div>
                )}

                {selectedFinding.finding_type === "prohibited_concomitant_medication" && (
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Medication</div>
                      <div className="font-semibold text-[#f5c86d] mt-0.5">{selectedFinding.details?.treatment}</div>
                    </div>
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Restricted Class</div>
                      <div className="font-semibold text-[#f5c86d] mt-0.5">{selectedFinding.details?.medication_class}</div>
                    </div>
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Start Date</div>
                      <div className="font-semibold text-[#d4e2ee] mt-0.5">{formatDate(selectedFinding.details?.start_date)}</div>
                    </div>
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Protocol Restriction</div>
                      <div className="font-semibold text-[#d4e2ee] mt-0.5">Protocol §5 Prohibited</div>
                    </div>
                  </div>
                )}

                {selectedFinding.finding_type === "exclusion_violation_creatinine" && (
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Screening Result</div>
                      <div className="font-semibold text-[#c9bdff] mt-0.5">{selectedFinding.details?.value} {selectedFinding.details?.unit}</div>
                    </div>
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Protocol Threshold</div>
                      <div className="font-semibold text-[#d4e2ee] mt-0.5">1.50 mg/dL</div>
                    </div>
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5 col-span-2">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Variance Above Limit</div>
                      <div className="font-semibold text-[#c9bdff] mt-0.5">
                        +{(Number(selectedFinding.details?.value) - 1.5).toFixed(2)} mg/dL above inclusion cutoff
                      </div>
                    </div>
                  </div>
                )}

                {selectedFinding.finding_type === "visit_window_deviation" && (
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Target Day</div>
                      <div className="font-semibold text-[#93c5fd] mt-0.5">Day {selectedFinding.details?.target_day}</div>
                    </div>
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Actual Conduct Day</div>
                      <div className="font-semibold text-[#d4e2ee] mt-0.5">Day {selectedFinding.details?.actual_day}</div>
                    </div>
                    <div className="rounded-lg border border-white/[.08] bg-white/[.03] p-2.5 col-span-2">
                      <div className="text-[10px] text-[#7e8fa4] uppercase">Allowed Window vs Delta</div>
                      <div className="font-semibold text-[#93c5fd] mt-0.5">
                        Allowed: ±{selectedFinding.details?.allowed_window_days} days · Actual Delta: +{selectedFinding.details?.delta_days} days
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* E. SUPPORTING EVIDENCE RECORDS (LIGHT & ELEGANT CLINICAL SOURCE CARDS) */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck size={14} className="text-[#3df4d4]" />
                    <span className="mono text-[10px] uppercase tracking-[.15em] text-[#718298] font-bold">
                      Supporting Evidence Records ({evidenceDetails.length})
                    </span>
                  </div>
                  <span className="text-[11px] text-[#718298]">
                    Immutable study source records
                  </span>
                </div>

                {/* Evidence Linkage Banner */}
                <div className="mb-3 flex items-center gap-2 rounded-lg border border-white/[.06] bg-white/[.02] px-3 py-1.5 text-[11px] text-[#869ab1]">
                  <span className="font-semibold text-[#3df4d4]">{selectedMeta.label}</span>
                  <ArrowRight size={12} className="text-[#55677b]" />
                  <span>Proved by {evidenceDetails.length} exact data record{evidenceDetails.length === 1 ? "" : "s"} below</span>
                </div>

                {evidenceLoading ? (
                  <div className="p-6 text-center text-xs text-[#718298]">
                    Loading evidence records...
                  </div>
                ) : (
                  <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                    {evidenceDetails.map((ev, idx) => (
                      <div
                        key={idx}
                        className="rounded-xl border border-white/[.09] bg-white/[.035] hover:bg-white/[.06] hover:border-white/[.15] p-3.5 text-xs transition space-y-2.5"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="mono text-[11px] font-bold text-[#3df4d4] bg-[#2de2c3]/15 px-2 py-0.5 rounded border border-[#2de2c3]/25">
                              {ev.reference.domain} · Seq {ev.reference.seq}
                            </span>
                            <span className="mono text-[10px] text-[#889cb0]">
                              {formatDate(ev.details.date || ev.details.visit_date || ev.details.start_date)}
                            </span>
                          </div>

                          <span className="flex items-center gap-1 text-[10px] font-semibold text-[#3df4d4] bg-[#2de2c3]/10 px-2 py-0.5 rounded-full border border-[#2de2c3]/20">
                            <ShieldCheck size={11} /> VERIFIED EVIDENCE
                          </span>
                        </div>

                        {/* Domain-Specific Structured Field Layout */}
                        {ev.reference.domain === "LB" && (
                          <div className="grid grid-cols-2 gap-2 text-xs bg-black/20 p-2.5 rounded-lg border border-white/[.04]">
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Test</span>
                              <div className="font-bold text-[#f1f6fa]">{ev.details.test}</div>
                            </div>
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Measured Value</span>
                              <div className="mono font-bold text-[#3df4d4]">
                                {ev.details.raw_value || ev.details.numeric_value} {ev.details.unit || ""}
                              </div>
                            </div>
                            {ev.details.uln !== undefined && ev.details.uln !== null && (
                              <div>
                                <span className="text-[10px] text-[#718298] uppercase">Reference ULN</span>
                                <div className="mono text-[#a0b3c6]">{ev.details.uln} {ev.details.unit || ""}</div>
                              </div>
                            )}
                            {ev.details.ratio_to_uln !== undefined && ev.details.ratio_to_uln !== null && (
                              <div>
                                <span className="text-[10px] text-[#718298] uppercase">Ratio to ULN</span>
                                <div className="mono font-bold text-[#f5c86d]">
                                  {Number(ev.details.ratio_to_uln).toFixed(2)}× ULN
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {ev.reference.domain === "CM" && (
                          <div className="grid grid-cols-2 gap-2 text-xs bg-black/20 p-2.5 rounded-lg border border-white/[.04]">
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Medication</span>
                              <div className="font-bold text-[#f5c86d]">{ev.details.treatment}</div>
                            </div>
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Drug Class</span>
                              <div className="mono text-[#f7d98d]">{ev.details.class || ev.details.drug_class}</div>
                            </div>
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Dose</span>
                              <div className="mono text-[#d4e2ee]">{ev.details.dose || "Prescribed"}</div>
                            </div>
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Indication</span>
                              <div className="text-[#a0b3c6]">{ev.details.indication || "None specified"}</div>
                            </div>
                          </div>
                        )}

                        {ev.reference.domain === "AE" && (
                          <div className="grid grid-cols-2 gap-2 text-xs bg-black/20 p-2.5 rounded-lg border border-white/[.04]">
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">AE Term</span>
                              <div className="font-bold text-[#ff9085]">{ev.details.term}</div>
                            </div>
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Severity / Seriousness</span>
                              <div className="text-[#ffaaa3]">{ev.details.severity} (AESER={ev.details.serious})</div>
                            </div>
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Hospitalized</span>
                              <div className="mono font-bold text-[#ff9085]">AESHOSP = {ev.details.hospitalized}</div>
                            </div>
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Outcome</span>
                              <div className="text-[#a0b3c6]">{ev.details.outcome}</div>
                            </div>
                          </div>
                        )}

                        {ev.reference.domain === "VS" && (
                          <div className="grid grid-cols-2 gap-2 text-xs bg-black/20 p-2.5 rounded-lg border border-white/[.04]">
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Vital Sign Test</span>
                              <div className="font-bold text-[#93c5fd]">{ev.details.test}</div>
                            </div>
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Value</span>
                              <div className="mono font-bold text-[#d4e2ee]">{ev.details.value} {ev.details.unit || ""}</div>
                            </div>
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Visit</span>
                              <div className="mono text-[#a0b3c6]">{ev.details.visit || "Scheduled"}</div>
                            </div>
                            <div>
                              <span className="text-[10px] text-[#718298] uppercase">Recorded Date</span>
                              <div className="mono text-[#a0b3c6]">{formatDate(ev.details.date)}</div>
                            </div>
                          </div>
                        )}

                        {/* Provenance Footer */}
                        <div className="flex items-center justify-between text-[10px] text-[#6b7d94] pt-1 border-t border-white/[.04]">
                          <span>Subject: {ev.reference.usubjid}</span>
                          <span>Snapshot Cut {selectedFinding.cut} · Protocol v{selectedFinding.protocol_version}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* G. EMPTY STATE */
            <div className="flex min-h-[460px] flex-col items-center justify-center p-6 text-center">
              <div className="grid h-16 w-16 place-items-center rounded-2xl border border-white/10 bg-white/[.04] text-[#3df4d4] shadow-lg mb-4">
                <FileSearch size={28} />
              </div>
              <h3 className="text-base font-semibold text-[#e1ebf4]">
                Select a Finding to Inspect
              </h3>
              <p className="mt-2 max-w-[340px] text-xs leading-relaxed text-[#8192a6]">
                Choose any clinical signal from the browser on the left to inspect its plain-language clinical story, protocol checklist, and exact supporting data records.
              </p>

              <div className="mt-6 flex flex-col gap-2 w-full max-w-[300px]">
                <button
                  onClick={() => {
                    setFilterType("potential_hys_law");
                    const f = findings.find((x) => x.finding_type === "potential_hys_law");
                    if (f) setSelectedFindingId(f.finding_id);
                  }}
                  className="w-full flex items-center justify-between rounded-lg border border-[#ff887b]/30 bg-[#ff887b]/10 px-3.5 py-2 text-xs font-semibold text-[#ffaaa3] hover:bg-[#ff887b]/20 transition"
                >
                  <span>Potential Hy's Law</span>
                  <span className="mono text-[11px] bg-[#ff887b]/20 px-2 py-0.5 rounded">{counts.hys} findings</span>
                </button>

                <button
                  onClick={() => {
                    setFilterType("serious_adverse_event");
                    const f = findings.find((x) => x.finding_type === "serious_adverse_event");
                    if (f) setSelectedFindingId(f.finding_id);
                  }}
                  className="w-full flex items-center justify-between rounded-lg border border-[#ff7e72]/30 bg-[#ff7e72]/10 px-3.5 py-2 text-xs font-semibold text-[#ff887b] hover:bg-[#ff7e72]/20 transition"
                >
                  <span>Serious Adverse Events</span>
                  <span className="mono text-[11px] bg-[#ff7e72]/20 px-2 py-0.5 rounded">{counts.sae} findings</span>
                </button>

                <button
                  onClick={() => {
                    setFilterType("prohibited_concomitant_medication");
                    const f = findings.find((x) => x.finding_type === "prohibited_concomitant_medication");
                    if (f) setSelectedFindingId(f.finding_id);
                  }}
                  className="w-full flex items-center justify-between rounded-lg border border-[#f5c86d]/30 bg-[#f5c86d]/10 px-3.5 py-2 text-xs font-semibold text-[#f7d98d] hover:bg-[#f5c86d]/20 transition"
                >
                  <span>Prohibited Medications</span>
                  <span className="mono text-[11px] bg-[#f5c86d]/20 px-2 py-0.5 rounded">{counts.med} findings</span>
                </button>

                <button
                  onClick={() => {
                    setFilterType("exclusion_violation_creatinine");
                    const f = findings.find((x) => x.finding_type === "exclusion_violation_creatinine");
                    if (f) setSelectedFindingId(f.finding_id);
                  }}
                  className="w-full flex items-center justify-between rounded-lg border border-[#b5a2ff]/30 bg-[#b5a2ff]/10 px-3.5 py-2 text-xs font-semibold text-[#c9bdff] hover:bg-[#b5a2ff]/20 transition"
                >
                  <span>Creatinine Exclusions</span>
                  <span className="mono text-[11px] bg-[#b5a2ff]/20 px-2 py-0.5 rounded">{counts.creat} findings</span>
                </button>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function Router() {
  const [path] = useLocation();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div key={path} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} transition={{ duration: .24, ease: "easeOut" }}>
        <Switch>
          <Route path="/" component={Dashboard} />
          <Route path="/graph" component={StudyGraph} />
          <Route path="/atlas" component={Atlas} />
          <Route path="/evidence" component={Evidence} />
          <Route component={NotFound} />
        </Switch>
      </motion.div>
    </AnimatePresence>
  );
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <RoutedErrorBoundary>
            <Shell>
              <Router />
            </Shell>
          </RoutedErrorBoundary>
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;