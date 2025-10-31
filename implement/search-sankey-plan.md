# Implementation Plan - Transaction Search & Sankey Chart
**Created:** 2025-10-30
**Session:** search-and-sankey

## Source Analysis
- **Source Type**: Feature request
- **Core Features**:
  1. Search bar for transactions (quick filter)
  2. Sankey diagram showing category flows
- **Dependencies**: May need plotly for Sankey chart
- **Complexity**: Medium

## Feature 1: Transaction Search Bar

### Requirements
- Quick search across transaction fields (payee, notes, category)
- Real-time filtering as user types
- Clear/reset search functionality
- Search state persistence during session

### Integration Points
- Add search field to transaction filters
- Update TransactionState with search field
- Filter transactions based on search query

## Feature 2: Sankey Chart

### Requirements
- Visualize money flow between categories
- Show income vs expenses
- Interactive chart
- Use category hierarchy if applicable

### Research Needed
- Check if Reflex supports Sankey charts
- Plotly integration with Reflex
- Data structure for Sankey (source, target, value)

### Data Mapping
```
Income categories → Spending categories
Amount flows between categories
```

## Target Integration

**Affected Files:**
1. `sankash/pages/transactions.py` - Add search bar
2. `sankash/state/transaction_state.py` - Add search field and filtering
3. `sankash/pages/dashboard.py` (or new chart page) - Sankey visualization
4. `sankash/state/dashboard_state.py` - Sankey data preparation
5. `pyproject.toml` - May need to add plotly dependency

## Implementation Tasks

### Phase 1: Transaction Search ✅
- [x] Analyze current transaction filtering
- [x] Add search_query field to TransactionState
- [x] Create search input component with icon
- [x] Implement search filtering logic (case-insensitive)
- [x] Add clear search button (X icon)
- [x] Add on_blur to trigger search
- [x] Update clear_filters to include search

### Phase 2: Sankey Chart Research ✅
- [x] Check Reflex charting capabilities (rx.plotly supported)
- [x] Plotly already in dependencies
- [x] prepare_sankey_data already exists in analytics_service
- [x] Dashboard already has Sankey placeholder

### Phase 3: Sankey Implementation ✅
- [x] Import plotly.graph_objects in DashboardState
- [x] Create sankey_figure computed var
- [x] Build Plotly Sankey with proper node/link structure
- [x] Replace placeholder with rx.plotly component
- [x] Add empty state handling
- [x] Style chart with proper layout

### Phase 4: Testing ✅
- [x] App compiles with zero warnings
- [x] Search component integrated
- [x] Sankey chart integrated
- [ ] User testing: Search functionality
- [ ] User testing: Sankey visualization

## Validation Checklist
- [ ] Search filters transactions correctly
- [ ] Search is case-insensitive
- [ ] Sankey chart displays
- [ ] Chart shows correct category flows
- [ ] App compiles successfully
- [ ] No performance issues
- [ ] Logging added to new features

## Technical Considerations

**Search Implementation:**
- Case-insensitive search
- Search across: payee, notes, category
- Debouncing (optional for performance)
- Combine with existing filters

**Sankey Chart:**
- Need source → target → value data
- Possible flows:
  - Income categories → Expense categories
  - All categories → spending patterns
  - Account → Category flows

## Risk Mitigation
- **Potential Issues**:
  - Plotly may not integrate smoothly with Reflex
  - Sankey data structure complexity
  - Performance with large datasets
- **Rollback Strategy**: Features are additive, easy to remove
