import React, { useState } from 'react';
import { SitePulse, SiteStatus } from '../../lib/reviewApi';
import { Building2 } from 'lucide-react';

interface SitePulseMatrixProps {
  sites: SitePulse[];
  selectedSiteId?: string | null;
  onSelectSite: (siteId: string | null) => void;
}

export const SitePulseMatrix: React.FC<SitePulseMatrixProps> = ({
  sites,
  selectedSiteId,
  onSelectSite,
}) => {
  const [hoveredSite, setHoveredSite] = useState<SitePulse | null>(null);

  const getStatusStyle = (status: SiteStatus) => {
    switch (status) {
      case 'stable':
        return {
          dot: 'bg-[#10b981]',
          badge: 'bg-[#f0fdf4] text-[#15803d] border-[#bbf7d0]',
        };
      case 'watch':
        return {
          dot: 'bg-[#f59e0b]',
          badge: 'bg-[#fffbeb] text-[#b45309] border-[#fde68a]',
        };
      case 'attention':
        return {
          dot: 'bg-[#f43f5e]',
          badge: 'bg-[#fff1f2] text-[#be123c] border-[#fecdd3]',
        };
    }
  };

  return (
    <div className="flex flex-col h-full rounded-2xl border border-[#cbd5e1]/60 bg-white/90 p-5 shadow-[0_12px_36px_rgba(100,140,180,0.08)] backdrop-blur-xl justify-between">
      <div>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-[#0d9488]" />
            <h3 className="mono text-[11px] font-bold uppercase tracking-[.18em] text-[#0f172a]">
              Site Pulse
            </h3>
          </div>
          {selectedSiteId && (
            <button
              onClick={() => onSelectSite(null)}
              className="text-xs mono font-semibold text-[#0d9488] hover:underline"
            >
              Clear filter ({selectedSiteId}) ✕
            </button>
          )}
        </div>
        <p className="text-xs text-[#64748b] mb-4">
          Factual review status derived from queries & recurring issue volume across 12 study sites
        </p>

        {/* 12-Site Matrix (4 columns x 3 rows) */}
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-2.5">
          {sites.map((site) => {
            const statusStyle = getStatusStyle(site.status);
            const isSelected = selectedSiteId === site.siteId;

            return (
              <div
                key={site.siteId}
                onClick={() => onSelectSite(isSelected ? null : site.siteId)}
                onMouseEnter={() => setHoveredSite(site)}
                onMouseLeave={() => setHoveredSite(null)}
                className={`relative p-3 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? 'border-[#0d9488] bg-[#f0fdfa] ring-2 ring-[#0d9488]/20 shadow-xs'
                    : 'border-[#e2e8f0] bg-white hover:border-[#0d9488]/40 hover:bg-[#f8fafc] hover:shadow-xs'
                }`}
              >
                {/* Header: Site ID & Status Dot */}
                <div className="flex items-center justify-between">
                  <span className="mono text-xs font-bold text-[#0f172a] tracking-wider">
                    {site.siteId}
                  </span>
                  <span
                    className={`w-2 h-2 rounded-full ${statusStyle.dot}`}
                    title={`Status: ${site.status}`}
                  />
                </div>

                {/* Counts */}
                <div className="mt-2 text-[10px] mono text-[#64748b] space-y-0.5">
                  <div className="flex justify-between">
                    <span>Cases:</span>
                    <strong className="text-[#0f172a] font-semibold">{site.openCases}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Queries:</span>
                    <strong className={site.unansweredQueries > 0 ? 'text-[#b45309] font-bold' : 'text-[#0f172a] font-semibold'}>
                      {site.openQueries}
                    </strong>
                  </div>
                </div>

                {/* Status Pill */}
                <div className="mt-2 pt-1 border-t border-[#f1f5f9] flex items-center justify-between">
                  <span
                    className={`text-[9px] mono font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${statusStyle.badge}`}
                  >
                    {site.status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Dynamic Hover Details / Sub-footer */}
      <div className="mt-4 pt-3 border-t border-[#f1f5f9]">
        {hoveredSite ? (
          <div className="rounded-lg bg-[#f8fafc] border border-[#e2e8f0] p-2.5 text-xs text-[#0f172a] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="mono font-bold text-[#0d9488]">{hoveredSite.siteId}:</span>
              <span>{hoveredSite.statusReason}</span>
            </div>
            <span className="mono text-[10px] text-[#64748b]">Click to filter cases</span>
          </div>
        ) : (
          <div className="flex items-center justify-between text-xs mono text-[#64748b] px-0.5">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#10b981]" />
              <span>Stable (0-1 issues)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#f59e0b]" />
              <span>Watch (unanswered query)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#f43f5e]" />
              <span>Attention (recurring)</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
