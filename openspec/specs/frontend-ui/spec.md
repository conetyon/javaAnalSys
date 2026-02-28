# Frontend UI Capability

## Purpose
React-based web interface for browsing knowledge points and matching code snippets. Provides bilingual (Chinese/English) knowledge point tree, code syntax highlighting, and configurable matching parameters.

## Requirements

### Requirement: Knowledge Point Tree Browsing
The system SHALL provide a hierarchical tree view of all knowledge points with three levels (L1→L2→L3).

#### Scenario: Load knowledge point tree
- **WHEN** the Dashboard page loads
- **THEN** knowledge point tree is fetched from `/api/knowledge/tree`
- **AND** tree is displayed with expandable/collapsible nodes
- **AND** loading spinner is shown during fetch

#### Scenario: Display bilingual names
- **WHEN** knowledge point has both `name` and `name_zh` fields
- **THEN** Chinese name (`name_zh`) is displayed as primary text
- **AND** English name (`name`) is displayed as secondary gray text
- **AND** if `name_zh` is null, only English name is shown

#### Scenario: Expand/collapse tree nodes
- **WHEN** user clicks on a non-leaf node (L1 or L2)
- **THEN** node expands or collapses to show/hide children
- **AND** expanded state is persisted to sessionStorage
- **AND** clicking anywhere on the row triggers expand (not just the arrow)

#### Scenario: Search knowledge points
- **WHEN** user types in the search input
- **THEN** tree is filtered to show matching nodes
- **AND** search works with both Chinese and English names
- **AND** matching parent nodes remain visible

#### Scenario: Select leaf node for matching
- **WHEN** user clicks on a leaf node (L3)
- **THEN** matching request is triggered
- **AND** selected node is visually highlighted
- **AND** non-leaf nodes do not trigger matching

### Requirement: Code Snippet Matching
The system SHALL display matching code snippets when a knowledge point is selected.

#### Scenario: Display match results
- **WHEN** matching completes successfully
- **THEN** results are displayed as cards with rank number
- **AND** each card shows score, AST ratio, keyword score, difficulty
- **AND** total count is displayed above results

#### Scenario: Show code with syntax highlighting
- **WHEN** match result card is rendered
- **THEN** code content is displayed with Java syntax highlighting
- **AND** line numbers are shown

#### Scenario: Fold long code
- **WHEN** code snippet exceeds 20 lines
- **THEN** code is initially collapsed to 20 lines
- **AND** "展开全部 (N 行)" button is shown
- **AND** clicking expands to show full code

#### Scenario: Copy code to clipboard
- **WHEN** user clicks the copy button
- **THEN** code content is copied to clipboard
- **AND** success message is displayed

#### Scenario: Load more results
- **WHEN** user clicks "加载更多" button
- **THEN** `top_k` is increased by 5
- **AND** new request is made with updated parameter
- **AND** results list is replaced with new results

### Requirement: Parameter Configuration
The system SHALL allow users to configure matching parameters.

#### Scenario: Adjust top_k parameter
- **WHEN** user changes the "返回数量" input
- **THEN** value is updated in state
- **AND** next matching request uses new value

#### Scenario: Adjust target_difficulty parameter
- **WHEN** user drags the difficulty slider
- **THEN** slider moves smoothly (step=0.05)
- **AND** label shows current difficulty level (简单/中等/困难)
- **AND** tooltip explains parameter meaning

#### Scenario: Re-match with new parameters
- **WHEN** user clicks "重新匹配" button
- **THEN** new matching request is made with current parameters
- **AND** loading state is shown
- **AND** results are replaced

### Requirement: Error Handling
The system SHALL display meaningful error messages and provide retry options.

#### Scenario: Display API error
- **WHEN** API request fails
- **THEN** error alert is displayed with error message
- **AND** retry button is provided

#### Scenario: Handle empty results
- **WHEN** matching returns zero results
- **THEN** empty state message is displayed
- **AND** no error is shown

#### Scenario: Display loading state
- **WHEN** API request is in progress
- **THEN** loading spinner is displayed
- **AND** user interactions are not blocked

### Requirement: URL Parameter Support
The system SHALL support URL query parameters for deep linking.

#### Scenario: Parse URL parameters on load
- **WHEN** Dashboard loads with URL parameters (kp_ids, top_k, target_difficulty)
- **THEN** parameters are parsed and applied to state
- **AND** initial matching can be triggered based on parameters

## Implementation Details

### Technology Stack
- **Framework**: React 18 + TypeScript
- **UI Library**: Ant Design 5
- **Build Tool**: Vite
- **HTTP Client**: Axios
- **Syntax Highlighting**: react-syntax-highlighter (Prism theme)

### Directory Structure
```
frontend/src/
├── api/                  # API layer
│   ├── client.ts         # Axios instance with interceptors
│   ├── knowledge.ts      # Knowledge point API
│   └── match.ts          # Matching API
├── components/           # Reusable components
│   ├── KnowledgeTree.tsx # Tree with bilingual support
│   ├── CodeBlock.tsx     # Syntax highlighting
│   └── MatchResultCard.tsx # Result card with scores
├── pages/                # Page components
│   └── Dashboard.tsx     # Main page (sidebar + content)
├── types/                # TypeScript definitions
│   ├── api.ts            # Response types
│   ├── knowledge.ts      # KnowledgeTreeNode
│   ├── match.ts          # MatchResultItem
│   └── index.ts          # Re-exports
└── App.tsx               # Root with routing
```

### Key Components

#### KnowledgeTree.tsx
- Ant Design Tree component with custom rendering
- `expandAction="click"` for row-click expansion
- Bilingual display: `name_zh || name` with fallback
- Search filter supports both languages
- Badge showing child count for non-leaf nodes

#### CodeBlock.tsx
- react-syntax-highlighter with Prism
- Java language support
- Line numbers enabled

#### MatchResultCard.tsx
- Ant Design Card with custom title
- Score tags with color coding (green/blue/orange)
- Difficulty label with severity color
- Collapsible code (20 lines threshold)
- Copy to clipboard with message feedback

#### Dashboard.tsx
- Ant Design Layout with fixed Sider
- Parameter panel (InputNumber, Slider)
- Result list with loading/error/empty states
- URL parameter parsing via react-router-dom

### API Proxy Configuration
```typescript
// vite.config.ts
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
```

### Type Definitions

#### KnowledgeTreeNode
```typescript
interface KnowledgeTreeNode {
  id: number;
  name: string;
  name_zh: string | null;  // Chinese name (nullable)
  parent_id: number | null;
  level: number;
  children: KnowledgeTreeNode[];
  title: string;  // Backend-provided, equals name
  key: number;    // Backend-provided, equals id
}
```

#### MatchResultItem
```typescript
interface MatchResultItem {
  id: number | null;
  content: string;
  score: number;
  ast_ratio: number;
  keyword_score: number;
  keyword_hit: number;
  keyword_total: number;
  difficulty: number;
  file_path?: string;
}
```

## Dependencies
- react: ^18.2.0
- react-dom: ^18.2.0
- react-router-dom: ^6.x
- antd: ^5.x
- axios: ^1.x
- react-syntax-highlighter: ^15.x
- @types/react-syntax-highlighter: ^15.x
- typescript: ^5.x
- vite: ^5.x

## Future Iterations

### Iteration 2: User Authentication
- Login/Register pages
- JWT token management
- Route guards (PrivateRoute)
- Header component with user menu

### Iteration 3: Advanced Features
- Matrix mode (difficulty-grouped results)
- Composite matching (multi-KP selection)
- Match history page
- Favorites functionality
