# Implementation Plan - Category Management with Subcategories
**Created:** 2025-10-29 22:10
**Feature:** Dedicated Categories page with full subcategory support

## Source Analysis
- **Source Type:** Feature Request / Requirements
- **Core Features:**
  - Dedicated Categories management page
  - Add/Edit/Delete categories
  - Category and subcategory hierarchy
  - Assign subcategories to transactions (not just parent categories)
  - Rules assign subcategories
  - Sankey diagram uses both categories and subcategories
- **Dependencies:** None (all existing: Reflex, Polars, DuckDB)
- **Complexity:** Medium - UI, state management, database query updates

## Current State Analysis

**Database Schema (schema.sql:20-27):**
- ✅ Categories table exists with `parent_category` field
- ✅ Already supports hierarchy
- ✅ Transactions.category field stores category name (string)

**Services (category_service.py):**
- ✅ `get_categories()` - Get all categories
- ✅ `create_category()` - Create with parent_category support
- ✅ `update_category()` - Update category
- ✅ `delete_category()` - Delete and uncategorize transactions
- ✅ Already supports parent_category in seed data

**Current Limitations:**
- ❌ No dedicated Categories page in UI
- ❌ Transactions only show category, not specifically if it's a subcategory
- ❌ Rules might not be specifically assigning subcategories
- ❌ Sankey might not leverage hierarchy

## Target Integration

### New Files to Create:
1. `sankash/pages/categories.py` - New categories management page
2. `sankash/state/category_state.py` - State management for categories page

### Files to Modify:
3. `sankash/components/sidebar.py` - Add Categories nav link
4. `sankash/services/category_service.py` - Add helper functions for hierarchy
5. `sankash/pages/transactions.py` - Update category display to show hierarchy
6. `sankash/pages/rules.py` - Ensure rules can assign subcategories
7. `sankash/pages/dashboard.py` - Update Sankey to use hierarchy (when implemented)

## Implementation Tasks

### Phase 1: Category Service Enhancements
- [ ] Add `get_parent_categories()` function (categories with no parent)
- [ ] Add `get_subcategories(parent_name)` function
- [ ] Add `get_category_hierarchy()` function (returns tree structure)
- [ ] Add validation to prevent circular references
- [ ] Add helper to get full category path (e.g., "Income > Salary")

### Phase 2: Category State Management
- [ ] Create `CategoryState` class with form fields
- [ ] Add fields: name, parent_category, color, editing_id
- [ ] Add `load_categories()` method
- [ ] Add `create_category()` method
- [ ] Add `update_category()` method
- [ ] Add `delete_category()` method with confirmation
- [ ] Add `get_parent_options()` computed property
- [ ] Add form validation (unique names, no circular refs)

### Phase 3: Categories Page UI
- [ ] Create categories page with layout
- [ ] Add category creation form (name, parent dropdown, color picker)
- [ ] Display categories in hierarchical tree/list view
- [ ] Show category with subcategories indented
- [ ] Add edit button per category
- [ ] Add delete button with confirmation dialog
- [ ] Show transaction count per category
- [ ] Show total spending per category
- [ ] Add color preview for each category

### Phase 4: Sidebar Integration
- [ ] Add "Categories" nav link to sidebar (after Accounts, before Rules)
- [ ] Use appropriate icon (e.g., "tags" or "folder-tree")

### Phase 5: Transaction Updates
- [ ] Update transaction service to handle subcategory display
- [ ] Modify transaction list to show "Parent > Subcategory" format
- [ ] Ensure transaction categorization works with subcategories
- [ ] Update category dropdown to show hierarchy

### Phase 6: Rules Updates
- [ ] Verify rules can assign subcategories (should already work)
- [ ] Update rules UI to show category hierarchy in dropdowns
- [ ] Test rule application with subcategories

### Phase 7: Analytics/Sankey Updates (Future)
- [ ] Plan how Sankey will aggregate by parent category
- [ ] Option to show parent-level or subcategory-level flows
- [ ] Document approach for future Sankey implementation

## Validation Checklist
- [ ] Categories page accessible from sidebar
- [ ] Can create parent categories
- [ ] Can create subcategories under parents
- [ ] Can edit categories without breaking references
- [ ] Can delete categories (transactions get uncategorized)
- [ ] Categories display in hierarchy everywhere
- [ ] Transactions show "Parent > Subcategory" format
- [ ] Rules can assign subcategories
- [ ] No circular parent references possible
- [ ] Color picker works
- [ ] Transaction counts accurate
- [ ] App compiles with no warnings

## Risk Mitigation
- **Potential Issues:**
  - Circular parent references (solved with validation)
  - Deleting categories used by transactions (handled by uncategorizing)
  - Category name uniqueness across hierarchy
  - Performance with many categories/subcategories

- **Rollback Strategy:**
  - New page is additive (no breaking changes)
  - Database schema unchanged (uses existing parent_category)
  - Git checkpoint after each phase

## Architecture Decisions
1. **Use existing database schema** - No migration needed, parent_category already exists
2. **String-based category references** - Transactions reference category by name (current system)
3. **Hierarchical display** - Show as "Parent > Child" in UI
4. **Flat list in database** - Hierarchy derived from parent_category field
5. **Color inheritance** - Subcategories can have own colors or inherit from parent

## Expected Outcome
- Dedicated Categories management page
- Full CRUD operations for categories and subcategories
- Visual hierarchy in all category displays
- Better organization for budgeting and analysis
- Foundation for hierarchical Sankey diagram
