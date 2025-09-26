from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple


# --- The "Rulebook" Dataclasses ---

@dataclass
class AssetClass:
    """Represents the concept and hierarchy of an asset class."""
    name: str
    parent: Optional['AssetClass'] = None
    children: Dict[str, 'AssetClass'] = field(default_factory=dict)

    def find_ancestor_in(self, asset_class_names: List[str]) -> Optional['AssetClass']:
        """Finds the closest ancestor that is in the provided list of names."""
        current = self.parent
        while current:
            if current.name in asset_class_names:
                return current
            current = current.parent
        return None


@dataclass
class PortfolioLevel:
    """Represents a specific strategic allocation plan (e.g., PL2, PL3)."""
    name: str
    allocations: Dict[str, List[float]]  # Maps class names to risk allocations

    def get_allocation(self, asset_class_name: str, risk_index: int) -> float:
        """Safely gets the allocation for a given asset class and risk index."""
        risk_allocations = self.allocations.get(asset_class_name)
        if risk_allocations and 0 <= risk_index < len(risk_allocations):
            return risk_allocations[risk_index]
        return 0.0


class AllocationRules:
    """
    A container that loads and holds all the static rule data,
    parsing the raw dictionaries into structured objects.
    """

    def __init__(self, pl_dicts: List[Tuple[str, dict]], reduction_table: dict, tree_dict: dict):
        self._reduction_table = reduction_table
        self.asset_classes = self._build_asset_class_tree(tree_dict)
        self.portfolio_levels = {name: PortfolioLevel(name, data) for name, data in pl_dicts}

    def _build_asset_class_tree(self, tree_dict: dict) -> Dict[str, AssetClass]:
        asset_class_map = {}

        def recurse_build(node_dict, parent=None):
            for name, content in node_dict.items():
                asset_class = AssetClass(name=name, parent=parent)
                asset_class_map[name] = asset_class
                if parent:
                    parent.children[name] = asset_class
                recurse_build(content.get("children", {}), parent=asset_class)

        recurse_build(tree_dict)
        return asset_class_map

    def get_asset_class(self, name: str) -> Optional[AssetClass]:
        return self.asset_classes.get(name)

    def get_portfolio_level(self, name: str) -> Optional[PortfolioLevel]:
        return self.portfolio_levels.get(name)

    def get_reduction_pct(self, asset_class_name: str) -> float:
        """Safely gets the reduction percentage for a given asset class."""
        return self._reduction_table.get(asset_class_name, 0.0)

    def find_leaf_allocation(self, asset_class_name: str, risk_index: int) -> float:
        """Finds the allocation from the most detailed PL that defines it."""
        for pl_name in sorted(self.portfolio_levels.keys(), reverse=True):
            level = self.portfolio_levels[pl_name]
            if asset_class_name in level.allocations:
                return level.get_allocation(asset_class_name, risk_index)
        return 0.0


# --- Example Usage ---

if __name__ == "__main__":
    # Your existing data dictionaries
    PL4 = {"EQ_EM": [0.36, 1.08, 2.16, 3.6, 5.4, 7.2, 7.2], "EQ_US": [1.8, 8.4, 16.8, 28, 42, 56, 56],
           "EQ_JP": [0.2, 0.6, 1.2, 2, 3, 4, 4], "EQ_EU": [2.64, 0.92, 3.84, 6.4, 9.6, 12.8, 12.8],
           "BO_SEK": [4.3, 16.75, 28.35, 28.35, 15.75, 0, 0], "MM_SEK": [86.0, 60.0, 25, 5, 0, 0, 0],
           "HY_SEK": [1.44, 3.61, 6.49, 6.49, 3.61, 0, 0], "IG_SEK": [2.26, 5.64, 10.16, 10.16, 5.64, 0, 0],
           "EQ_SE": [1.0, 3.0, 6, 10, 15, 20, 20], }
    PL3 = {"EQ_SE": [1.0, 3.0, 6, 10, 15, 20, 20], "EQ_EM": [0.36, 1.08, 2.16, 3.6, 5.4, 7.2, 7.2],
           "EQ_WI": [4.64, 9.92, 21.84, 36.4, 54.6, 72.8, 72.8], "MM_SEK": [86.0, 60.0, 25, 5, 0, 0, 0],
           "BO_SEK": [4.3, 16.75, 28.35, 28.35, 15.75, 0, 0], "CR_SEK": [3.7, 9.25, 16.65, 16.65, 9.25, 0, 0], }
    PL2 = {"EQ_ACWI": [5.0, 11.0, 24.0, 40.0, 60.0, 80.0, 80.0], "FI_SEK": [8.0, 26.0, 45.0, 45.0, 25.0, 0, 0],
           "EQ_SE": [1.0, 3.0, 6, 10, 15, 20, 20], "MM_SEK": [86.0, 60.0, 25, 5, 0, 0, 0], }
    reduction_table = {"EQ_SE": 37.5, "EQ_US": 37.5, "EQ_EU": 37.5, "EQ_JP": 37.5, "EQ_EM": 37.5, "BO_SEK": 37.5,
                       "IG_SEK": 37.5, "HY_SEK": 37.5, "MM_SEK": 37.5, "EQ_WI": 25, "CR_SEK": 25, "EQ_ACWI": 12.5,
                       "FI_SEK": 12.5, }
    pl_dicts = [("PL2", PL2), ("PL3", PL3), ("PL4", PL4)]
    tree = {"EQ_ACWI": {"children": {"EQ_WI": {"children": {"EQ_US": {}, "EQ_EU": {}, "EQ_JP": {}}}, "EQ_EM": {}}},
            "FI_SEK": {"children": {"CR_SEK": {"children": {"HY_SEK": {}, "IG_SEK": {}}}, "BO_SEK": {}}}, }

    # 1. Create a single "rules" object from all the raw data
    rules = AllocationRules(pl_dicts, reduction_table, tree)

    # --- Now we can query the rules in an object-oriented way ---
    print("--- Querying the Allocation Rules ---")
    risk_index = 5  # Risk Level 6

    # Get a specific Portfolio Level
    pl3_level = rules.get_portfolio_level("PL3")
    if pl3_level:
        eq_wi_alloc = pl3_level.get_allocation('EQ_WI', risk_index)
        print(f"In {pl3_level.name}, the allocation for EQ_WI at risk {risk_index + 1} is: {eq_wi_alloc}%")

        # Now add the reduction table logic
        eq_wi_reduction_pct = rules.get_reduction_pct('EQ_WI')
        headroom = eq_wi_alloc * (eq_wi_reduction_pct / 100)
        print(
            f"The maximum satellite allocation for EQ_WI is {eq_wi_reduction_pct}%, which becomes {headroom:.2f}% of the overall portfolio")

    # Get a specific Asset Class and inspect its hierarchy
    eq_jp_class = rules.get_asset_class("EQ_JP")
    if eq_jp_class and eq_jp_class.parent:
        print(f"The asset class '{eq_jp_class.name}' has parent '{eq_jp_class.parent.name}'.")

    # Use a method to find the "leaf" allocation for a granular class
    leaf_alloc_jp = rules.find_leaf_allocation("EQ_JP", risk_index)
    print(f"The most detailed ('leaf') allocation for EQ_JP at risk {risk_index + 1} is: {leaf_alloc_jp}%")