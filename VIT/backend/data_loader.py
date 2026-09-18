import os
import glob
import pandas as pd
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

class DataLoader:
    """
    Robust data loader for ATLAS Clinical Trial datasets.
    Handles domain tables, reference ranges, cuts, and corrections.
    """
    DOMAIN_FILES = {
        "DM": "DM.csv",
        "AE": "AE.csv",
        "LB": "LB.csv",
        "VS": "VS.csv",
        "EX": "EX.csv",
        "CM": "CM.csv",
        "DS": "DS.csv",
        "MH": "MH.csv",
        "EG": "EG.csv"
    }

    SEQ_FIELDS = {
        "AE": "AESEQ",
        "LB": "LBSEQ",
        "VS": "VSSEQ",
        "EX": "EXSEQ",
        "CM": "CMSEQ",
        "DS": "DSSEQ",
        "MH": "MHSEQ",
        "EG": "EGSEQ"
    }

    MONTH_MAP = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
    }

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self._raw_cache: Dict[str, pd.DataFrame] = {}
        self.reference_ranges: pd.DataFrame = pd.DataFrame()
        self.corrections: pd.DataFrame = pd.DataFrame()
        self.cuts: pd.DataFrame = pd.DataFrame()

    @staticmethod
    def parse_date(date_str: Any) -> Optional[str]:
        """
        Parses multiple date formats (e.g. YYYY-MM-DD or DD-MMM-YYYY) to ISO YYYY-MM-DD.
        """
        if pd.isna(date_str) or not str(date_str).strip():
            return None
        s = str(date_str).strip()
        # Check ISO YYYY-MM-DD
        if len(s) == 10 and s[4] == '-' and s[7] == '-':
            return s
        # Check DD-MMM-YYYY (e.g. 03-FEB-2026)
        parts = s.split('-')
        if len(parts) == 3:
            day, month_str, year = parts[0], parts[1].upper(), parts[2]
            if month_str in DataLoader.MONTH_MAP and len(year) == 4:
                day_fmt = day.zfill(2)
                month_fmt = DataLoader.MONTH_MAP[month_str]
                return f"{year}-{month_fmt}-{day_fmt}"
        return s

    @staticmethod
    def parse_lab_value(val: Any) -> Tuple[bool, Optional[float], str]:
        """
        Safely parses lab result values into (is_numeric, numeric_value, raw_value).
        Non-numeric values like '<5', 'ND', blank are preserved as non-numeric.
        """
        if pd.isna(val) or val is None:
            return False, None, ""
        s = str(val).strip()
        if not s:
            return False, None, ""
        
        # Check special non-numeric cases
        if s.startswith("<") or s.startswith(">") or s.upper() in ["ND", "NOT DONE", "BLANK"]:
            return False, None, s
        
        # Replace comma decimal separators if present (e.g. "12,4")
        clean_s = s.replace(',', '.')
        try:
            num = float(clean_s)
            return True, num, s
        except ValueError:
            return False, None, s

    def load(self, cut: Optional[int] = None) -> Dict[str, pd.DataFrame]:
        """
        Loads all clinical domain tables filtered by data cut and with corrections applied.
        """
        # Load metadata files if present
        ref_file = self.data_dir / "reference_ranges.csv"
        if ref_file.exists():
            self.reference_ranges = pd.read_csv(ref_file, dtype=str)

        corr_file = self.data_dir / "corrections.csv"
        if corr_file.exists():
            self.corrections = pd.read_csv(corr_file, dtype=str)

        cuts_file = self.data_dir / "cuts.csv"
        if cuts_file.exists():
            self.cuts = pd.read_csv(cuts_file, dtype=str)

        loaded_tables: Dict[str, pd.DataFrame] = {}

        for domain, filename in self.DOMAIN_FILES.items():
            filepath = self.data_dir / filename
            if not filepath.exists():
                continue

            df = pd.read_csv(filepath, dtype=str).fillna("")

            # Filter by cut_available if cut is specified
            if cut is not None and "cut_available" in df.columns:
                df["cut_available_int"] = pd.to_numeric(df["cut_available"], errors="coerce").fillna(999)
                df = df[df["cut_available_int"] <= cut].drop(columns=["cut_available_int"])

            # Apply corrections if applicable
            if not self.corrections.empty and domain in self.SEQ_FIELDS:
                seq_col = self.SEQ_FIELDS[domain]
                domain_corrs = self.corrections[self.corrections["domain"] == domain]
                
                if cut is not None:
                    domain_corrs["cut_int"] = pd.to_numeric(domain_corrs["cut"], errors="coerce").fillna(999)
                    domain_corrs = domain_corrs[domain_corrs["cut_int"] <= cut]

                for _, corr in domain_corrs.iterrows():
                    subj = corr["usubjid"]
                    seq_val = corr["seq"]
                    field = corr["field"]
                    new_val = corr["new_value"]
                    corr_cut = corr["cut"]

                    # Find matching row in DataFrame
                    mask = (df["USUBJID"] == subj) & (df[seq_col] == seq_val)
                    if mask.any() and field in df.columns:
                        df.loc[mask, field] = new_val
                        df.loc[mask, "corrected_at_cut"] = corr_cut

            loaded_tables[domain] = df

        return loaded_tables
