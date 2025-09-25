from collections import defaultdict

def split_reduction_among_satellites(core_pl, reduction_table, tree, pl_dicts, risk_index, satellite_classes):
    # First, prepare to find parents and the right leaf PL for limits
    satellites_info = []
    for satellite_class in satellite_classes:
        parent_class = find_satellite_parent(tree, core_pl.keys(), satellite_class)
        leaf_PL_name, leaf_PL = find_leaf_PL(pl_dicts, satellite_class)
        if leaf_PL is not None:
            leaf_limit = leaf_PL[satellite_class][risk_index]
        else:
            leaf_limit = 0
        satellites_info.append({
            'satellite_class': satellite_class,
            'parent_class': parent_class,
            'leaf_PL_name': leaf_PL_name,
            'leaf_limit': leaf_limit
        })

    # Now, group satellites by their parent class
    satellites_by_parent = defaultdict(list)
    for info in satellites_info:
        if info['parent_class']:
            satellites_by_parent[info['parent_class']].append(info)

    # Make the new portfolio starting from core_pl
    new_portfolio = core_pl.copy()
    results = []

    for parent_class, satellites in satellites_by_parent.items():
        headroom_total = core_pl[parent_class] * (reduction_table.get(parent_class, 0) / 100)
        even_share = headroom_total / len(satellites)
        parent_alloc = new_portfolio[parent_class]

        for info in satellites:
            alloc = min(even_share, info['leaf_limit'])
            info['allocated'] = alloc
            info['parent_start_alloc'] = parent_alloc
            new_portfolio[info['satellite_class']] = alloc
            parent_alloc -= alloc
            info['parent_end_alloc'] = parent_alloc
            info['reduction_allowed'] = headroom_total
            info['reduction_used'] = alloc
            results.append(info)

        new_portfolio[parent_class] = parent_alloc  # After all satellites for this parent

    return new_portfolio, results

def find_satellite_parent(tree, core_pl_keys, target, path=None):
    """
    Recursively find the closest ancestor of 'target' in the tree that is present in core_pl_keys.
    Returns the name of that ancestor.
    """
    if path is None:
        path = []

    for name, node in tree.items():
        new_path = path + [name]
        if name == target:
            # climb up the path to find first in core_pl_keys (ignoring the current node itself)
            for parent in reversed(path):
                if parent in core_pl_keys:
                    return parent
            return None
        res = find_satellite_parent(node.get('children', {}), core_pl_keys, target, new_path)
        if res:
            return res
    return None

def max_satellite_allocation(core_pl, pl_name, reduction_table, tree, pl4, risk_index, satellite_class):
    """
    Given the core portfolio allocations and parameters, returns:
    - the relevant parent in core_pl
    - that parent's allocation for this risk
    - the max allowed satellite allocation considering reduction and leaf allocation
    """
    parent_class = find_satellite_parent(tree, core_pl.keys(), satellite_class)
    if parent_class is None:
        raise ValueError(f"No ancestor of {satellite_class} found in portfolio core.")

    parent_alloc = core_pl[parent_class][risk_index]
    reduction_pct = reduction_table.get(parent_class, 0)
    reduction_limit = parent_alloc * (reduction_pct / 100)
    leaf_limit = pl4.get(satellite_class, [0]*7)[risk_index]

    satellite_alloc = min(reduction_limit, leaf_limit)
    return {
        'parent_class': parent_class,
        'parent_alloc': parent_alloc,
        'max_allocation': satellite_alloc,
        'reduction_limit': reduction_limit,
        'leaf_limit': leaf_limit,
    }

PL4 = {
  "EQ_EM": [
    0.36,
    1.08,
    2.16,
    3.6,
    5.4,
    7.2,
    7.2
  ],
  "EQ_US": [
    1.8,
    8.4,
    16.8,
    28,
    42,
    56,
    56
  ],
  "EQ_JP": [
    0.2,
    0.6,
    1.2,
    2,
    3,
    4,
    4
  ],
  "EQ_EU": [
    2.64,
    0.92,
    3.84,
    6.4,
    9.6,
    12.8,
    12.8
  ],
  "BO_SEK": [
    4.3,
    16.75,
    28.35,
    28.35,
    15.75,
    0,
    0
  ],
  "MM_SEK": [
    86.0,
    60.0,
    25,
    5,
    0,
    0,
    0
  ],
  "HY_SEK": [
    1.44,
    3.61,
    6.49,
    6.49,
    3.61,
    0,
    0
  ],
  "IG_SEK": [
    2.26,
    5.64,
    10.16,
    10.16,
    5.64,
    0,
    0
  ],
  "EQ_SE": [
    1.0,
    3.0,
    6,
    10,
    15,
    20,
    20
  ]
}

PL3 = {
  "EQ_SE": [
    1.0,
    3.0,
    6,
    10,
    15,
    20,
    20
  ],
  "EQ_EM": [
    0.36,
    1.08,
    2.16,
    3.6,
    5.4,
    7.2,
    7.2
  ],
  "EQ_WI": [
    4.64,
    9.92,
    21.84,
    36.4,
    54.6,
    72.8,
    72.8
  ],
  "MM_SEK": [
    86.0,
    60.0,
    25,
    5,
    0,
    0,
    0
  ],
  "BO_SEK": [
    4.3,
    16.75,
    28.35,
    28.35,
    15.75,
    0,
    0
  ],
  "CR_SEK": [
    3.7,
    9.25,
    16.65,
    16.65,
    9.25,
    0,
    0
  ]
}

PL2 = {
  "EQ_ACWI": [
    5.0,
    11.0,
    24.0,
    40.0,
    60.0,
    80.0,
    80.0
  ],
  "FI_SEK": [
    8.0,
    26.0,
    45.0,
    45.0,
    25.0,
    0,
    0
  ],
  "EQ_SE": [
    1.0,
    3.0,
    6,
    10,
    15,
    20,
    20
  ],
  "MM_SEK": [
    86.0,
    60.0,
    25,
    5,
    0,
    0,
    0
  ]
}


reduction_table = {
    'EQ_SE': 37.5,
    'EQ_US': 37.5,
    'EQ_EU': 37.5,
    'EQ_JP': 37.5,
    'EQ_EM': 37.5,
    'BO_SEK': 37.5,
    'IG_SEK': 37.5,
    'HY_SEK': 37.5,
    'MM_SEK': 37.5,
    'EQ_WI': 25,
    'CR_SEK': 25,
    'EQ_ACWI': 12.5,
    'FI_SEK': 12.5,
}


def node(pl2=None, pl3=None, pl4=None, children=None):
    return {'PL2': pl2, 'PL3': pl3, 'PL4': pl4, 'children': children or {}}

# Now, fill in allocations where possible:
risk_index = 5  # risk level 6 (since zero indexed)
satellite_class = 'EQ_JP'

# The tree structure from above (for finding parents)
tree = {
    "EQ_ACWI": {
        'PL2': None, 'PL3': None, 'PL4': None,
        "children": {
            "EQ_WI": {'PL2': None, 'PL3': None, 'PL4': None,
                "children": {
                    "EQ_US": {'PL2': None, 'PL3': None, 'PL4': None, 'children': {}},
                    "EQ_EU": {'PL2': None, 'PL3': None, 'PL4': None, 'children': {}},
                    "EQ_JP": {'PL2': None, 'PL3': None, 'PL4': None, 'children': {}},
                }
            },
            "EQ_EM": {'PL2': None, 'PL3': None, 'PL4': None, 'children': {}}
        }
    },
    "EQ_SE": {'PL2': None, 'PL3': None, 'PL4': None, 'children': {}},
    "FI_SEK": {'PL2': None, 'PL3': None, 'PL4': None, "children": {}},
    "MM_SEK": {'PL2': None, 'PL3': None, 'PL4': None, 'children': {}}
}

# Find ancestor in core_pl for our satellite
def find_satellite_parent(node, core_keys, target, path=None):
    if path is None:
        path = []
    for name, entry in node.items():
        new_path = path + [name]
        if name == target:
            # Climb up the path to find first in core_keys
            for parent in reversed(path):
                if parent in core_keys:
                    return parent
            return None
        res = find_satellite_parent(entry.get('children', {}), core_keys, target, new_path)
        if res:
            return res
    return None

# Compute max allowed
def max_satellite_allocation(core_pl, reduction_table, tree, pl4, risk_index, satellite_class):
    parent_class = find_satellite_parent(tree, core_pl.keys(), satellite_class)
    if parent_class is None:
        raise ValueError("Satellite class has no ancestor in portfolio core")
    parent_alloc = core_pl[parent_class]
    reduction_pct = reduction_table.get(parent_class, 0)
    reduction_limit = parent_alloc * (reduction_pct / 100)
    leaf_limit = pl4.get(satellite_class, [0]*7)[risk_index]
    satellite_alloc = min(reduction_limit, leaf_limit)
    return {
        'parent_class': parent_class,
        'parent_alloc': parent_alloc,
        'max_allocation': satellite_alloc,
        'reduction_limit': reduction_limit,
        'leaf_limit': leaf_limit,
    }
core_pl = {'EQ_SE': 20, 'EQ_EM': 7.2, 'EQ_WI': 72.8, 'MM_SEK': 0, 'BO_SEK': 0, 'CR_SEK': 0}

from collections import defaultdict

def add_satellites(core_pl, reduction_table, tree, pl4, risk_index, satellite_classes):
    # Copy so we don't modify original
    new_portfolio = core_pl.copy()
    # Track, for each parent, total reduction allocated
    reduction_used = defaultdict(float)
    satellite_results = []

    for satellite_class in satellite_classes:
        # 1. Find parent in portfolio tree
        parent_class = find_satellite_parent(tree, core_pl.keys(), satellite_class)
        if parent_class is None:
            print(f"Skipping {satellite_class}: no parent in portfolio core.")
            continue

        parent_alloc = new_portfolio[parent_class]
        reduction_pct = reduction_table.get(parent_class, 0)
        reduction_max_total = core_pl[parent_class] * (reduction_pct / 100)  # Allowed headroom *at start*
        reduction_remaining = reduction_max_total - reduction_used[parent_class]

        leaf_limit = pl4.get(satellite_class, [0]*7)[risk_index]
        # Satellite fund can be at most its leaf allocation or remaining reduction headroom, whichever is smaller
        allowed = min(reduction_remaining, leaf_limit)

        if allowed > 0:
            # Subtract from parent, add as its own node
            new_portfolio[satellite_class] = allowed
            new_portfolio[parent_class] -= allowed
            reduction_used[parent_class] += allowed

        satellite_results.append({
            'satellite_class': satellite_class,
            'parent_class': parent_class,
            'parent_start_alloc': core_pl[parent_class],
            'parent_end_alloc': new_portfolio[parent_class],
            'reduction_pct': reduction_pct,
            'reduction_allowed': reduction_max_total,
            'reduction_used': reduction_used[parent_class],
            'leaf_limit': leaf_limit,
            'allocated': allowed
        })

    return new_portfolio, satellite_results

# EXAMPLE USAGE:

def find_leaf_PL(pl_dicts, satellite_class):
  for name, pl in reversed(pl_dicts):  # start from the finest
    if satellite_class in pl:
      return name, pl
  return None, None  # not found
def add_satellites_dynamic(core_pl, reduction_table, tree, pl_dicts, risk_index, satellite_classes):
    """
    Adds satellites and always uses the most detailed available PL
    for each satellite as the leaf limit.
    - pl_dicts: see find_leaf_PL
    Returns: new_portfolio, [per-satellite info]
    """
    from collections import defaultdict
    new_portfolio = core_pl.copy()
    reduction_used = defaultdict(float)
    satellite_results = []

    for satellite_class in satellite_classes:
        parent_class = find_satellite_parent(tree, core_pl.keys(), satellite_class)
        if parent_class is None:
            print(f"Skipping {satellite_class}: no parent in portfolio core.")
            continue

        parent_alloc = new_portfolio[parent_class]
        reduction_pct = reduction_table.get(parent_class, 0)
        reduction_max_total = core_pl[parent_class] * (reduction_pct / 100)
        reduction_remaining = reduction_max_total - reduction_used[parent_class]

        # --- DYNAMIC leaf/PL lookup here ---
        leaf_PL_name, leaf_PL = find_leaf_PL(pl_dicts, satellite_class)
        if leaf_PL is not None:
            leaf_limit = leaf_PL[satellite_class][risk_index]
        else:
            leaf_limit = 0  # not found

        allowed = min(reduction_remaining, leaf_limit)
        if allowed > 0:
            new_portfolio[satellite_class] = allowed
            new_portfolio[parent_class] -= allowed
            reduction_used[parent_class] += allowed

        satellite_results.append({
            'satellite_class': satellite_class,
            'parent_class': parent_class,
            'parent_start_alloc': core_pl[parent_class],
            'parent_end_alloc': new_portfolio[parent_class],
            'reduction_pct': reduction_pct,
            'reduction_allowed': reduction_max_total,
            'reduction_used': reduction_used[parent_class],
            'leaf_limit': leaf_limit,
            'allocated': allowed,
            'used_leaf_PL': leaf_PL_name
        })

    return new_portfolio, satellite_results
# core_pl, reduction_table, tree, PL4, risk_index as above

# List/dict of available PLs, from least to most detailed
pl_dicts = [('PL2', PL2), ('PL3', PL3), ('PL4', PL4)]

core_pl = {k: PL2[k][5] for k in PL2}      # PL2 at risk 6
satellites = ['EQ_WI', 'EQ_JP', 'EQ_US'] 
risk_index = 5

def split_reduction_with_leaf_limits(core_pl, reduction_table, tree, pl_dicts, risk_index, satellite_classes):
    # Prepare lookup tables as before
    satellites_info = []
    for satellite_class in satellite_classes:
        parent_class = find_satellite_parent(tree, core_pl.keys(), satellite_class)
        leaf_PL_name, leaf_PL = find_leaf_PL(pl_dicts, satellite_class)
        leaf_limit = leaf_PL[satellite_class][risk_index] if leaf_PL is not None else 0
        satellites_info.append({
            'satellite_class': satellite_class,
            'parent_class': parent_class,
            'leaf_PL_name': leaf_PL_name,
            'leaf_limit': leaf_limit
        })

    satellites_by_parent = defaultdict(list)
    for info in satellites_info:
        if info['parent_class']:
            satellites_by_parent[info['parent_class']].append(info)

    new_portfolio = core_pl.copy()
    results = []

    for parent_class, satellites in satellites_by_parent.items():
        headroom_total = core_pl[parent_class] * (reduction_table.get(parent_class, 0) / 100)
        satellites = sorted(satellites, key=lambda x: x['leaf_limit'])  # Allocate small first if you want
        
        parent_alloc = new_portfolio[parent_class]

        for info in satellites:
            allowed = min(info['leaf_limit'], headroom_total)
            info['allocated'] = allowed
            info['parent_start_alloc'] = parent_alloc
            new_portfolio[info['satellite_class']] = allowed
            parent_alloc -= allowed
            headroom_total -= allowed
            info['parent_end_alloc'] = parent_alloc
            info['reduction_allowed'] = headroom_total
            info['reduction_used'] = allowed
            results.append(info)

        new_portfolio[parent_class] = parent_alloc

    return new_portfolio, results

# --- Usage Example (same as before) ---

core_pl = {k: PL3[k][5] for k in PL3}  # PL3 at risk 6
satellites = ['EQ_US', "EQ_EU"]
pl_dicts = [('PL2', PL2), ('PL3', PL3), ('PL4', PL4)]
risk_index = 5


new_portfolio, satinfo = split_reduction_with_leaf_limits(core_pl, reduction_table, tree, pl_dicts, risk_index, satellites)

print("New portfolio with improved fill:")
for k, v in new_portfolio.items():
    print(f"{k}: {v:.2f}%")

print("\nSatellite allocation details:")
for sat in satinfo:
    print(
        f"{sat['satellite_class']}: allocated {sat['allocated']:.2f}% (parent: {sat['parent_class']})," +
        f" leaf limit: {sat['leaf_limit']:.2f}%, parent now {sat['parent_end_alloc']:.2f}%"
    )

def fineprint():
  def print_pl_table(pl, pl_name="PL"):
    # Collect all asset classes
    asset_classes = sorted(pl.keys())
    num_risks = max(len(v) for v in pl.values())

    # Header
    header = ["Risk"] + asset_classes
    print(f"\n=== {pl_name} Portfolio Allocation Table ===")
    print("{:<5}".format(header[0]), end="")
    for ac in asset_classes:
        print("{:>10}".format(ac), end="")
    print("\n" + "-" * (10 * (len(asset_classes) + 1)))

    for risk_idx in range(num_risks):
        print("{:<5}".format(risk_idx + 1), end="")  # Risk level 1-based
        for ac in asset_classes:
            val = pl[ac][risk_idx] if risk_idx < len(pl[ac]) else ""
            print("{:10.2f}".format(val), end="")
        print()

# Example usage for PL2, PL3, PL4:
  print_pl_table(PL2, "PL2")
  print_pl_table(PL3, "PL3")
  print_pl_table(PL4, "PL4")
