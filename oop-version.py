from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
import pprint

# ==============================================================================
# 1. CORE DATA DEFINITIONS (Unchanged)
# ==============================================================================
PL4 = {
    "EQ_EM": [0.36, 1.08, 2.16, 3.6, 5.4, 7.2, 7.2], "EQ_US": [1.8, 8.4, 16.8, 28, 42, 56, 56],
    "EQ_JP": [0.2, 0.6, 1.2, 2, 3, 4, 4], "EQ_EU": [2.64, 0.92, 3.84, 6.4, 9.6, 12.8, 12.8],
    "BO_SEK": [4.3, 16.75, 28.35, 28.35, 15.75, 0, 0], "MM_SEK": [86.0, 60.0, 25, 5, 0, 0, 0],
    "HY_SEK": [1.44, 3.61, 6.49, 6.49, 3.61, 0, 0], "IG_SEK": [2.26, 5.64, 10.16, 10.16, 5.64, 0, 0],
    "EQ_SE": [1.0, 3.0, 6, 10, 15, 20, 20],
}
PL3 = {
    "EQ_SE": [1.0, 3.0, 6, 10, 15, 20, 20], "EQ_EM": [0.36, 1.08, 2.16, 3.6, 5.4, 7.2, 7.2],
    "EQ_WI": [4.64, 9.92, 21.84, 36.4, 54.6, 72.8, 72.8], "MM_SEK": [86.0, 60.0, 25, 5, 0, 0, 0],
    "BO_SEK": [4.3, 16.75, 28.35, 28.35, 15.75, 0, 0], "CR_SEK": [3.7, 9.25, 16.65, 16.65, 9.25, 0, 0],
}
PL2 = {
    "EQ_ACWI": [5.0, 11.0, 24.0, 40.0, 60.0, 80.0, 80.0], "FI_SEK": [8.0, 26.0, 45.0, 45.0, 25.0, 0, 0],
    "EQ_SE": [1.0, 3.0, 6, 10, 15, 20, 20], "MM_SEK": [86.0, 60.0, 25, 5, 0, 0, 0],
}
reduction_table = {
    "EQ_SE": 37.5, "EQ_US": 37.5, "EQ_EU": 37.5, "EQ_JP": 37.5, "EQ_EM": 37.5,
    "BO_SEK": 37.5, "IG_SEK": 37.5, "HY_SEK": 37.5, "MM_SEK": 37.5, "EQ_WI": 25,
    "CR_SEK": 25, "EQ_ACWI": 12.5, "FI_SEK": 12.5,
}
pl_dicts = [("PL2", PL2), ("PL3", PL3), ("PL4", PL4)]
tree = {
    "EQ_ACWI": {"children": {"EQ_WI": {"children": {"EQ_US": {}, "EQ_EU": {}, "EQ_JP": {}}}, "EQ_EM": {}}},
    "FI_SEK": {"children": {"CR_SEK": {"children": {"HY_SEK": {}, "IG_SEK": {}}}, "BO_SEK": {}}},
}

# ==============================================================================
# 2. THE "RULEBOOK" DATACLASSES (Unchanged)
# ==============================================================================
@dataclass(frozen=True, eq=True)
class AssetClass:
    name: str; parent: Optional['AssetClass'] = None
    children: Dict[str, 'AssetClass'] = field(default_factory=dict, hash=False, compare=False)
    def find_ancestor_in(self, names: List[str]) -> Optional['AssetClass']:
        c = self
        while c:
            if c.name in names: return c
            c = c.parent
        return None
@dataclass
class PortfolioLevel:
    name: str; allocations: Dict[str, List[float]]
    def get_allocation(self, name: str, risk: int) -> float:
        a = self.allocations.get(name)
        if a and 0 <= risk < len(a): return a[risk]
        return 0.0
class AllocationRules:
    def __init__(self, pls: List[Tuple[str, dict]], rt: dict, t: dict):
        self._rt = rt
        self.asset_classes = self._build_tree(pls, t)
        self.portfolio_levels = {n: PortfolioLevel(n, d) for n, d in pls}
    def _build_tree(self, pls, t: dict) -> Dict[str, AssetClass]:
        acm = {cn: AssetClass(name=cn) for _, d in pls for cn in d}
        def rb(nd, p=None):
            for n, c in nd.items():
                aco = acm.get(n)
                if aco:
                    object.__setattr__(aco, 'parent', p)
                    if p: p.children[n] = aco
                    rb(c.get("children", {}), p=aco)
        rb(t); return acm
    def get_asset_class(self, n: str) -> Optional[AssetClass]: return self.asset_classes.get(n)
    def get_portfolio_level(self, n: str) -> Optional[PortfolioLevel]: return self.portfolio_levels.get(n)
    def get_reduction_pct(self, n: str) -> float: return self._rt.get(n, 0.0)
    def find_leaf_allocation(self, n: str, r: int) -> float:
        for pn in sorted(self.portfolio_levels.keys(), reverse=True):
            l = self.portfolio_levels[pn]
            if n in l.allocations: return l.get_allocation(n, r)
        return 0.0

# ==============================================================================
# 3. THE "PORTFOLIO" DATACLASSES (With Reasoning Added)
# ==============================================================================

@dataclass
class Fund:
    name: str
    asset_class: AssetClass

@dataclass
class PortfolioHolding:
    fund: Fund
    allocation: float
    # **NEW**: Fields to store reasoning for satellites
    is_satellite: bool = False
    leaf_limit: Optional[float] = None
    competing_share: Optional[float] = None

class Portfolio:
    def __init__(self, name: str, rules: AllocationRules):
        self.name, self.rules = name, rules
        self.holdings: Dict[str, PortfolioHolding] = {}
        self.core_asset_classes: List[str] = []

    @classmethod
    def build_from_level(cls, name: str, pl_name: str, risk: int, funds: Dict[str, Fund], rules: AllocationRules):
        p = cls(name, rules)
        level = rules.get_portfolio_level(pl_name)
        if not level: raise ValueError(f"PL '{pl_name}' not found.")
        for cn, _ in level.allocations.items():
            fund = funds.get(cn)
            if fund:
                alloc = level.get_allocation(cn, risk)
                if alloc > 0:
                    p.holdings[fund.name] = PortfolioHolding(fund, alloc)
                    p.core_asset_classes.append(cn)
        return p

    def add_satellites(self, satellite_funds: List[Fund], risk_index: int):
        sats = [s for s in satellite_funds if s.name not in self.holdings]
        s_by_cf = defaultdict(list)
        for sf in sats:
            ancestor = sf.asset_class.find_ancestor_in(self.core_asset_classes)
            if ancestor:
                for h in self.holdings.values():
                    if h.fund.asset_class.name == ancestor.name:
                        s_by_cf[h.fund.name].append(sf); break
        
        for cfn, sfs in s_by_cf.items():
            ch = self.holdings[cfn]
            headroom = ch.allocation * (self.rules.get_reduction_pct(ch.fund.asset_class.name) / 100)
            swl = [{'f': s, 'lim': self.rules.find_leaf_allocation(s.asset_class.name, risk_index)} for s in sfs]
            ss = sorted(swl, key=lambda x: x['lim'])
            rem = len(ss)
            for si in ss:
                if rem <= 0 or headroom <= 1e-9: si['alloc'] = 0; continue
                share = headroom / rem
                alloc = min(si['lim'], share)
                si['alloc'], si['share'], headroom, rem = alloc, share, headroom - alloc, rem - 1
            
            for si in ss:
                if si['alloc'] > 0:
                    # **MODIFIED**: Create holding with reasoning data
                    self.holdings[si['f'].name] = PortfolioHolding(
                        fund=si['f'], allocation=si['alloc'], is_satellite=True,
                        leaf_limit=si['lim'], competing_share=si['share']
                    )
                    ch.allocation -= si['alloc']
    
    def display(self):
        print(f"\n--- Portfolio Display: {self.name} ---")
        grouped = defaultdict(list)
        for h in self.holdings.values():
            a = h.fund.asset_class.find_ancestor_in(self.core_asset_classes)
            if a: grouped[a.name].append(h)
        
        for cn, hs in sorted(grouped.items()):
            budget = sum(h.allocation for h in hs)
            headroom = budget * (self.rules.get_reduction_pct(cn) / 100)
            print(f"\nAsset class: {cn} (Total: {budget:.2f}%, Satellite space: {headroom:.2f}%)")
            print("-" * 55)
            for h in sorted(hs, key=lambda i: i.fund.name):
                print(f"    - {h.fund.name:<45}: {h.allocation:.2f}%")
                # **NEW**: Print reasoning if it's a satellite
                if h.is_satellite:
                    reason = ""
                    # Use a small tolerance for float comparison
                    if abs(h.allocation - h.leaf_limit) < 1e-9 and h.allocation < h.competing_share:
                        reason = f"Limited by its leaf limit of {h.leaf_limit:.2f}%"
                    else:
                        reason = f"Limited by its share of Satellite space ({h.competing_share:.2f}%)"
                    print(f"      └── Reasoning: {reason}")

        total = sum(h.allocation for h in self.holdings.values())
        print(f"\n{'='*20} TOTAL PORTFOLIO ALLOCATION: {total:.2f}% {'='*20}")

# ==============================================================================
# 4. SCRIPT EXECUTION
# ==============================================================================

if __name__ == "__main__":
    rules = AllocationRules(pl_dicts, reduction_table, tree)
    
    print("="*60, "\nDEMONSTRATING FULL PORTFOLIO ALLOCATION\n" + "="*60)
    
    core_funds_map = {
        "EQ_WI": Fund("EQ_WI Core Fund", rules.get_asset_class("EQ_WI")),
        "EQ_SE": Fund("EQ_SE Core Fund", rules.get_asset_class("EQ_SE")),
        "EQ_EM": Fund("EQ_EM Core Fund", rules.get_asset_class("EQ_EM")),
        
    }
    
    portfolio = Portfolio.build_from_level("My PL3 Portfolio", "PL3", 5, core_funds_map, rules)
    print(f"\nInitial Portfolio: PL3 risk 6")
    portfolio.display()
    
    satellites_to_add = [
        Fund("EQ_JP Satellite Fund", rules.get_asset_class("EQ_JP")),
        Fund("EQ_US Satellite Fund", rules.get_asset_class("EQ_US")),
        Fund("EQ_SE Satellite Fund", rules.get_asset_class("EQ_SE")),
        Fund("EQ_EU Satellite Fund", rules.get_asset_class("EQ_EU")),
    ]
    
    portfolio.add_satellites(satellites_to_add, 5)
    
    print("\n\nFinal Portfolio (After Adding Satellites):")
    portfolio.display()
