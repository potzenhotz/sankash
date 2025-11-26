# Implementation Plan - Category Display Enhancement
**Created**: 2025-10-31T21:10:00Z

## Source Analysis
- **Source Type**: Feature description
- **Core Features**:
  - Make parent categories more prominent in display
  - Show subcategories visually underneath parents (not as "under xyz")
  - Add subtle color indicators next to categories
  - Improve visual hierarchy and aesthetics
- **Complexity**: Medium - UI/UX enhancement

## Current State Analysis
**Current Implementation** (sankash/pages/categories.py:177-244):
- All categories shown in flat list with `rx.foreach`
- Subcategories show "under xyz" badge (line 202-206)
- Small 4px color bar on left side (line 182-187)
- No visual grouping of parent/subcategories

**Issues to Fix**:
1. Flat list doesn't show hierarchy visually
2. "under xyz" badge is not prominent enough
3. Color indicator is too subtle (only 4px bar)
4. No visual distinction between parent and child categories

## Target Integration
**Integration Points**:
- `sankash/pages/categories.py` - Update category display components
- `sankash/state/category_state.py` - May need hierarchical data structure

**Affected Files**:
- `sankash/pages/categories.py:177-244` - Rewrite category display logic
- `sankash/state/category_state.py` - Add hierarchy computation if needed

## Implementation Tasks

### Phase 1: Analyze Current Category State
- [x] Read current category_state.py to understand data structure
- [ ] Identify if hierarchical grouping logic exists
- [ ] Plan data transformation for hierarchical display

### Phase 2: Design New Display Components
- [ ] Create prominent parent category component
  - Larger heading/size
  - Full-width color indicator or background tint
  - Icon or visual marker
- [ ] Create indented subcategory component
  - Smaller size, indented
  - Subtle color dot/circle next to name
  - Clear parent-child relationship
- [ ] Remove "under xyz" badge approach

### Phase 3: Implement Hierarchical Grouping
- [ ] Add method to group categories by parent
- [ ] Create nested display structure
- [ ] Ensure proper ordering (parents first, then children)

### Phase 4: Enhance Visual Styling
- [ ] Add subtle color circles/dots next to category names
- [ ] Use category color for background tints (very low opacity)
- [ ] Improve spacing and indentation
- [ ] Add visual separators between category groups

### Phase 5: Testing & Validation
- [ ] Test with no categories
- [ ] Test with only parent categories
- [ ] Test with parent + subcategories
- [ ] Test with deeply nested hierarchies
- [ ] Verify colors display correctly

## Design Approach

**Parent Category Display**:
```
┌─────────────────────────────────────────────┐
│ 🔵 Food & Dining                            │  ← Larger, bold, color dot
│ ├─ Groceries              🟢               │  ← Indented subcategory
│ ├─ Restaurants            🟡               │  ← Subtle color indicator
│ └─ Coffee Shops           🟣               │
└─────────────────────────────────────────────┘
```

**Visual Hierarchy Elements**:
- Parent: Larger text (size 4), bold weight, color circle (12px)
- Child: Normal text (size 3), regular weight, indented 24px, color dot (8px)
- Background: Subtle tint using category color at 5% opacity

## Validation Checklist
- [ ] Parent categories visually distinct
- [ ] Subcategories clearly nested under parents
- [ ] Color indicators visible but subtle
- [ ] No "under xyz" badges
- [ ] Proper indentation/spacing
- [ ] Edit/delete buttons still functional
- [ ] App compiles without errors

## Risk Mitigation
- **Potential Issues**:
  - Breaking existing category edit/delete functionality
  - Performance with many categories
  - State management for nested structure
- **Rollback Strategy**: Git checkpoint before changes
