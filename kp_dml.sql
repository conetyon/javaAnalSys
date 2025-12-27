-- kp_dml.sql
-- Java Knowledge Points DML (hierarchical: domain -> module -> atomic points)
-- Idempotent: uses INSERT ... ON DUPLICATE KEY UPDATE (MySQL 5.7/8.0 compatible).
-- Re-running this script will upsert by primary key (id). semantic_vec is preserved on duplicates.
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =========================
-- Domain layer (level = 1)
-- =========================
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(1, 'Core Syntax & Types', NULL, 1, NULL, NULL, NULL),
(2, 'Control Flow', NULL, 1, NULL, NULL, NULL),
(3, 'OOP Fundamentals', NULL, 1, NULL, NULL, NULL),
(4, 'Encapsulation & Modifiers', NULL, 1, NULL, NULL, NULL),
(5, 'Generics', NULL, 1, NULL, NULL, NULL),
(6, 'Exceptions', NULL, 1, NULL, NULL, NULL),
(7, 'Collections', NULL, 1, NULL, NULL, NULL),
(8, 'Streams & Functional', NULL, 1, NULL, NULL, NULL),
(9, 'Lambda & Method References', NULL, 1, NULL, NULL, NULL),
(10, 'Optional', NULL, 1, NULL, NULL, NULL),
(11, 'Concurrency', NULL, 1, NULL, NULL, NULL),
(12, 'I/O & NIO', NULL, 1, NULL, NULL, NULL),
(13, 'Date & Time', NULL, 1, NULL, NULL, NULL),
(14, 'Annotations & Reflection', NULL, 1, NULL, NULL, NULL),
(15, 'Modules & Packaging', NULL, 1, NULL, NULL, NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- =========================
-- Module layer (level = 2)
-- =========================
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(101, 'Primitives & Strings', 1, 2, NULL, NULL, NULL),
(102, 'Arrays & Variables', 1, 2, NULL, NULL, NULL),

(201, 'Conditionals & Switch', 2, 2, NULL, NULL, NULL),
(202, 'Loops & Jumps', 2, 2, NULL, NULL, NULL),

(301, 'Classes & Members', 3, 2, NULL, NULL, NULL),
(302, 'Inheritance & Polymorphism', 3, 2, NULL, NULL, NULL),

(401, 'Access & Final', 4, 2, NULL, NULL, NULL),
(402, 'Static & Inner', 4, 2, NULL, NULL, NULL),

(501, 'Generic Types', 5, 2, NULL, NULL, NULL),
(502, 'Wildcards & Bounds', 5, 2, NULL, NULL, NULL),

(601, 'Handling Basics', 6, 2, NULL, NULL, NULL),
(602, 'Advanced Exception Handling', 6, 2, NULL, NULL, NULL),

(701, 'List', 7, 2, NULL, NULL, NULL),
(702, 'Set', 7, 2, NULL, NULL, NULL),
(703, 'Map', 7, 2, NULL, NULL, NULL),
(704, 'Queue & Deque', 7, 2, NULL, NULL, NULL),

(801, 'Streams', 8, 2, NULL, NULL, NULL),
(802, 'Collectors & Terminal Operations', 8, 2, NULL, NULL, NULL),

(901, 'Lambda', 9, 2, NULL, NULL, NULL),
(902, 'Method References & Functional Utilities', 9, 2, NULL, NULL, NULL),

(1001, 'Optional Basics', 10, 2, NULL, NULL, NULL),
(1002, 'Optional Advanced', 10, 2, NULL, NULL, NULL),

(1101, 'Threads & Synchronization', 11, 2, NULL, NULL, NULL),
(1102, 'Executors & Locks', 11, 2, NULL, NULL, NULL),

(1201, 'IO Streams', 12, 2, NULL, NULL, NULL),
(1202, 'NIO Files & Channels', 12, 2, NULL, NULL, NULL),

(1301, 'Core Time Types', 13, 2, NULL, NULL, NULL),
(1302, 'Formatting & Duration', 13, 2, NULL, NULL, NULL),

(1401, 'Annotations', 14, 2, NULL, NULL, NULL),
(1402, 'Reflection', 14, 2, NULL, NULL, NULL),

(1501, 'Packages & Imports', 15, 2, NULL, NULL, NULL),
(1502, 'Java Modules', 15, 2, NULL, NULL, NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- ============================================
-- Knowledge point layer (level = 3, 100 items)
-- ============================================

-- Domain 1: Core Syntax & Types (Modules: 101, 102) [6 items]
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10001, 'Primitive types: int/double/boolean', 101, 3,
  '{"template":"PrimitiveType","required_nodes":["integral_type","floating_point_type","boolean_type","int","double"],"details":["primitive"]}',
  '["int","double","boolean","primitive","type"]', NULL),
(10002, 'Type casting and promotion', 102, 3,
  '{"template":"PrimitiveType","required_nodes":["cast_expression","type_cast","primitive_type"],"details":["cast"]}',
  '["cast","type_cast","primitive","conversion"]', NULL),
(10003, 'String operations basics', 101, 3,
  '{"template":"Class","required_nodes":["type_identifier","string","method_invocation","substring","indexof","length"],"details":["java.lang.string"]}',
  '["string","substring","indexof","length","java.lang.string"]', NULL),
(10004, 'StringBuilder and StringBuffer', 101, 3,
  '{"template":"Class","required_nodes":["type_identifier","stringbuilder","stringbuffer","method_invocation","append","tostring"],"details":["java.lang"]}',
  '["stringbuilder","stringbuffer","append","tostring","java.lang"]', NULL),
(10005, 'Arrays basics', 102, 3,
  '{"template":"Class","required_nodes":["array_creation_expression","array_type","type_identifier","new"],"details":["array"]}',
  '["array","new","length","index"]', NULL),
(10006, 'var and local type inference', 102, 3,
  '{"template":"Class","required_nodes":["local_variable_declaration","var"],"details":["type_inference"]}',
  '["var","type_inference","local_variable"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 2: Control Flow (Modules: 201, 202) [6 items]
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10007, 'if-else basics', 201, 3,
  '{"template":"IfStatement","required_nodes":["if_statement"]}',
  '["if","else","condition"]', NULL),
(10008, 'switch statement', 201, 3,
  '{"template":"Class","required_nodes":["switch_statement","case","default"]}',
  '["switch","case","default"]', NULL),
(10009, 'switch expression', 201, 3,
  '{"template":"Class","required_nodes":["switch_expression","case","yield"]}',
  '["switch","expression","case","yield"]', NULL),
(10010, 'for loop', 202, 3,
  '{"template":"ForStatement","required_nodes":["for_statement"]}',
  '["for","loop","iteration"]', NULL),
(10011, 'while loop', 202, 3,
  '{"template":"WhileStatement","required_nodes":["while_statement"]}',
  '["while","loop","condition"]', NULL),
(10012, 'break and continue', 202, 3,
  '{"template":"Class","required_nodes":["break_statement","continue_statement"]}',
  '["break","continue","loop"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 3: OOP Fundamentals (Modules: 301, 302) [8 items]
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10013, 'Class declaration', 301, 3,
  '{"template":"Class","required_nodes":["class_declaration"]}',
  '["class","declaration"]', NULL),
(10014, 'Fields and methods', 301, 3,
  '{"template":"Class","required_nodes":["field_declaration","method_declaration"]}',
  '["field","method","member"]', NULL),
(10015, 'Constructors', 301, 3,
  '{"template":"Class","required_nodes":["constructor_declaration"]}',
  '["constructor","init"]', NULL),
(10016, 'this and super usage', 301, 3,
  '{"template":"Class","required_nodes":["this","super","method_declaration"]}',
  '["this","super","reference"]', NULL),
(10017, 'Inheritance: extends', 302, 3,
  '{"template":"Inheritance","required_nodes":["extends_clause","extends"]}',
  '["extends","superclass","inheritance"]', NULL),
(10018, 'Method overriding and @Override', 302, 3,
  '{"template":"Polymorphism","required_nodes":["method_declaration","override","@override"]}',
  '["override","polymorphism","method"]', NULL),
(10019, 'Interface declaration', 302, 3,
  '{"template":"Interface","required_nodes":["interface_declaration","interface"]}',
  '["interface","implements"]', NULL),
(10020, 'Abstract class and methods', 302, 3,
  '{"template":"Class","required_nodes":["abstract","class_declaration","method_declaration"]}',
  '["abstract","class","method"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 4: Encapsulation & Modifiers (Modules: 401, 402) [4 items]
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10021, 'Access modifiers: private/protected/public', 401, 3,
  '{"template":"Class","required_nodes":["private","protected","public","field_declaration","method_declaration"]}',
  '["access","private","protected","public","encapsulation"]', NULL),
(10022, 'final keyword usage', 401, 3,
  '{"template":"Class","required_nodes":["final","field_declaration","method_declaration"]}',
  '["final","constant","immutable"]', NULL),
(10023, 'static fields and methods', 402, 3,
  '{"template":"Class","required_nodes":["static","field_declaration","method_declaration"]}',
  '["static","class_member"]', NULL),
(10024, 'Inner and anonymous classes', 402, 3,
  '{"template":"Class","required_nodes":["class_declaration","anonymous_class_declaration"]}',
  '["inner_class","anonymous_class"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 5: Generics (Modules: 501, 502) [6 items]
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10025, 'Generic class declaration', 501, 3,
  '{"template":"Class","required_nodes":["generic_type","type_parameter","class_declaration"]}',
  '["generics","type_parameter","class"]', NULL),
(10026, 'Generic methods', 501, 3,
  '{"template":"Class","required_nodes":["type_parameter","method_declaration","generic_type"]}',
  '["generics","method","type_parameter"]', NULL),
(10027, 'Diamond operator', 501, 3,
  '{"template":"Class","required_nodes":["object_creation_expression","generic_type","diamond"]}',
  '["diamond","generics","new"]', NULL),
(10028, 'Wildcard ?', 502, 3,
  '{"template":"Class","required_nodes":["wildcard","type_argument"]}',
  '["wildcard","type_argument","generics"]', NULL),
(10029, 'Upper bound extends', 502, 3,
  '{"template":"Class","required_nodes":["type_bound","extends","type_argument"]}',
  '["extends","bound","generics"]', NULL),
(10030, 'Lower bound super', 502, 3,
  '{"template":"Class","required_nodes":["type_bound","super","type_argument"]}',
  '["super","bound","generics"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 6: Exceptions (Modules: 601, 602) [6 items]
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10031, 'try-catch basics', 601, 3,
  '{"template":"Exception","required_nodes":["try_statement","catch_clause"]}',
  '["try","catch","exception"]', NULL),
(10032, 'finally clause', 601, 3,
  '{"template":"Exception","required_nodes":["finally_clause","try_statement"]}',
  '["finally","cleanup","exception"]', NULL),
(10033, 'throw and throws', 601, 3,
  '{"template":"Exception","required_nodes":["throw_statement","throws"]}',
  '["throw","throws","exception"]', NULL),
(10034, 'try-with-resources', 602, 3,
  '{"template":"Exception","required_nodes":["try_statement","resource_specification","try_with_resources"]}',
  '["try-with-resources","autocloseable","resource"]', NULL),
(10035, 'Custom exception class', 602, 3,
  '{"template":"Class","required_nodes":["class_declaration","extends","exception"]}',
  '["extends","exception","runtimeexception"]', NULL),
(10036, 'Rethrow exceptions', 602, 3,
  '{"template":"Exception","required_nodes":["throw_statement","catch_clause"]}',
  '["rethrow","exception","throw"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 7: Collections (Modules: 701, 702, 703, 704) [16 items]
-- List
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10037, 'ArrayList basics', 701, 3,
  '{"template":"Declare<List>","required_nodes":["list","arraylist"],"details":["java.util.list"]}',
  '["java.util.list","arraylist","add","get","remove"]', NULL),
(10038, 'LinkedList basics', 701, 3,
  '{"template":"Declare<List>","required_nodes":["list","linkedlist"],"details":["java.util.list"]}',
  '["java.util.list","linkedlist","add","remove","get"]', NULL),
(10039, 'List add/remove/get', 701, 3,
  '{"template":"Declare<List>","required_nodes":["list","method_invocation","add","remove","get"],"details":["java.util.list"]}',
  '["java.util.list","add","remove","get","list"]', NULL),
(10040, 'List sorting with Comparator', 701, 3,
  '{"template":"Declare<List>","required_nodes":["list","method_invocation","sort","comparator"],"details":["java.util.list"]}',
  '["list","sort","comparator","java.util"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Set
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10041, 'HashSet basics', 702, 3,
  '{"template":"Declare<Set>","required_nodes":["set","hashset"],"details":["java.util.set"]}',
  '["java.util.set","hashset","add","contains","remove"]', NULL),
(10042, 'TreeSet basics', 702, 3,
  '{"template":"Declare<Set>","required_nodes":["set","treeset"],"details":["java.util.set"]}',
  '["java.util.set","treeset","comparator","add","remove"]', NULL),
(10043, 'Set add/remove/contains', 702, 3,
  '{"template":"Declare<Set>","required_nodes":["set","add","remove","contains"],"details":["java.util.set"]}',
  '["java.util.set","add","remove","contains","set"]', NULL),
(10044, 'LinkedHashSet basics', 702, 3,
  '{"template":"Declare<Set>","required_nodes":["set","linkedhashset"],"details":["java.util.set"]}',
  '["java.util.set","linkedhashset","order","add"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Map
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10045, 'HashMap basics', 703, 3,
  '{"template":"Class","required_nodes":["map","hashmap","type_identifier","object_creation_expression"],"details":["java.util.map"]}',
  '["java.util.map","hashmap","put","get","containskey"]', NULL),
(10046, 'LinkedHashMap basics', 703, 3,
  '{"template":"Class","required_nodes":["map","linkedhashmap","type_identifier"],"details":["java.util.map"]}',
  '["java.util.map","linkedhashmap","order","put","get"]', NULL),
(10047, 'TreeMap basics', 703, 3,
  '{"template":"Class","required_nodes":["map","treemap","type_identifier"],"details":["java.util.map"]}',
  '["java.util.map","treemap","comparator","put","get"]', NULL),
(10048, 'Map entrySet iteration', 703, 3,
  '{"template":"Class","required_nodes":["map","entryset","method_invocation","foreach"],"details":["java.util.map"]}',
  '["java.util.map","entryset","iterator","foreach"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Queue & Deque
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10049, 'ArrayDeque basics', 704, 3,
  '{"template":"Class","required_nodes":["deque","arraydeque","type_identifier","object_creation_expression"],"details":["java.util.deque"]}',
  '["java.util.deque","arraydeque","push","pop","peek"]', NULL),
(10050, 'PriorityQueue basics', 704, 3,
  '{"template":"Class","required_nodes":["queue","priorityqueue","type_identifier"],"details":["java.util.queue"]}',
  '["java.util.queue","priorityqueue","offer","poll","peek"]', NULL),
(10051, 'Queue offer/poll/peek', 704, 3,
  '{"template":"Class","required_nodes":["queue","offer","poll","peek","method_invocation"]}',
  '["java.util.queue","offer","poll","peek"]', NULL),
(10052, 'Deque push/pop', 704, 3,
  '{"template":"Class","required_nodes":["deque","push","pop","peek","method_invocation"]}',
  '["java.util.deque","push","pop","peek"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 8: Streams & Functional (Modules: 801, 802) [8 items]
-- Streams
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10053, 'Stream pipeline creation', 801, 3,
  '{"template":"Stream","required_nodes":["method_invocation","stream"]}',
  '["stream","pipeline","collection"]', NULL),
(10054, 'Intermediate operations: map/filter', 801, 3,
  '{"template":"Stream","required_nodes":["stream","map","filter"]}',
  '["stream","map","filter"]', NULL),
(10055, 'flatMap', 801, 3,
  '{"template":"Stream","required_nodes":["stream","flatmap"]}',
  '["stream","flatmap"]', NULL),
(10056, 'sorted and distinct', 801, 3,
  '{"template":"Stream","required_nodes":["stream","sorted","distinct"]}',
  '["stream","sorted","distinct"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Collectors & Terminal
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10057, 'collect toList/toSet', 802, 3,
  '{"template":"Stream","required_nodes":["stream","collect","tolist","toset","method_invocation"]}',
  '["stream","collect","collectors","tolist","toset"]', NULL),
(10058, 'reduce', 802, 3,
  '{"template":"Stream","required_nodes":["stream","reduce"]}',
  '["stream","reduce"]', NULL),
(10059, 'findFirst/findAny', 802, 3,
  '{"template":"Stream","required_nodes":["stream","findfirst","findany"]}',
  '["stream","findfirst","findany"]', NULL),
(10060, 'parallel streams', 802, 3,
  '{"template":"Stream","required_nodes":["stream","parallel","method_invocation"]}',
  '["stream","parallel","performance"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 9: Lambda & Method References (Modules: 901, 902) [6 items]
-- Lambda
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10061, 'Lambda expression basics', 901, 3,
  '{"template":"Lambda","required_nodes":["lambda_expression"]}',
  '["lambda","functional","expression"]', NULL),
(10062, 'Functional interfaces', 901, 3,
  '{"template":"Class","required_nodes":["functional_interface","@functionalinterface","interface_declaration"]}',
  '["functional_interface","@functionalinterface","interface"]', NULL),
(10063, 'Predicate and Function', 901, 3,
  '{"template":"Class","required_nodes":["predicate","function","type_identifier"]}',
  '["predicate","function","java.util.function"]', NULL),
(10064, 'Comparator with lambda', 901, 3,
  '{"template":"Class","required_nodes":["comparator","lambda_expression","method_invocation"]}',
  '["comparator","lambda","compare"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Method References & Functional Utilities
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10065, 'Method references', 902, 3,
  '{"template":"Class","required_nodes":["method_reference"]}',
  '["method_reference","lambda"]', NULL),
(10066, 'Consumer and Supplier', 902, 3,
  '{"template":"Class","required_nodes":["consumer","supplier","type_identifier"]}',
  '["consumer","supplier","java.util.function"]', NULL),
(10067, 'Stream forEach with method reference', 902, 3,
  '{"template":"Stream","required_nodes":["stream","foreach","method_reference"]}',
  '["stream","foreach","method_reference"]', NULL),
(10068, 'Function composition andThen', 902, 3,
  '{"template":"Class","required_nodes":["function","andthen","compose","method_invocation"]}',
  '["function","andthen","compose","java.util.function"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 10: Optional (Modules: 1001, 1002) [4 items]
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10069, 'Optional basics', 1001, 3,
  '{"template":"Class","required_nodes":["optional","type_identifier"]}',
  '["optional","java.util.optional","empty","of"]', NULL),
(10070, 'Optional map/filter/orElse', 1001, 3,
  '{"template":"Class","required_nodes":["optional","map","filter","orelse","method_invocation"]}',
  '["optional","map","filter","orelse"]', NULL),
(10071, 'orElseGet and ifPresent', 1002, 3,
  '{"template":"Class","required_nodes":["optional","orelseget","ifpresent","method_invocation"]}',
  '["optional","orelseget","ifpresent"]', NULL),
(10072, 'Optional flatMap', 1002, 3,
  '{"template":"Class","required_nodes":["optional","flatmap","method_invocation"]}',
  '["optional","flatmap"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 11: Concurrency (Modules: 1101, 1102) [8 items]
-- Threads & Synchronization
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10073, 'Thread creation: Thread/Runnable', 1101, 3,
  '{"template":"Class","required_nodes":["thread","runnable","type_identifier","object_creation_expression"]}',
  '["thread","runnable","start"]', NULL),
(10074, 'synchronized keyword', 1101, 3,
  '{"template":"Class","required_nodes":["synchronized","method_declaration"]}',
  '["synchronized","lock","monitor"]', NULL),
(10075, 'volatile variable', 1101, 3,
  '{"template":"Class","required_nodes":["volatile","field_declaration"]}',
  '["volatile","memory_visibility"]', NULL),
(10076, 'wait and notify', 1101, 3,
  '{"template":"Class","required_nodes":["wait","notify","method_invocation"]}',
  '["wait","notify","monitor"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Executors & Locks
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10077, 'ExecutorService submit', 1102, 3,
  '{"template":"Class","required_nodes":["executorservice","submit","type_identifier","method_invocation"]}',
  '["executorservice","submit","threadpool"]', NULL),
(10078, 'Future get', 1102, 3,
  '{"template":"Class","required_nodes":["future","get","type_identifier","method_invocation"]}',
  '["future","get","async"]', NULL),
(10079, 'ReentrantLock usage', 1102, 3,
  '{"template":"Class","required_nodes":["reentrantlock","lock","unlock","type_identifier","method_invocation"]}',
  '["reentrantlock","lock","unlock","concurrency"]', NULL),
(10080, 'AtomicInteger operations', 1102, 3,
  '{"template":"Class","required_nodes":["atomicinteger","getandincrement","type_identifier","method_invocation"]}',
  '["atomicinteger","getandincrement","atomic"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 12: I/O & NIO (Modules: 1201, 1202) [6 items]
-- IO Streams
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10081, 'FileInputStream and FileOutputStream', 1201, 3,
  '{"template":"Exception","required_nodes":["fileinputstream","fileoutputstream","inputstream","outputstream","method_invocation"]}',
  '["fileinputstream","fileoutputstream","read","write","io"]', NULL),
(10082, 'BufferedReader and BufferedWriter', 1201, 3,
  '{"template":"Exception","required_nodes":["bufferedreader","bufferedwriter","readline","method_invocation"]}',
  '["bufferedreader","bufferedwriter","readline","io"]', NULL),
(10083, 'PrintStream println', 1201, 3,
  '{"template":"Exception","required_nodes":["printstream","println","method_invocation"]}',
  '["printstream","println","io"]', NULL),
(10084, 'Charset and encoding', 1201, 3,
  '{"template":"Class","required_nodes":["charset","standardcharsets","type_identifier"]}',
  '["charset","standardcharsets","encoding"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- NIO Files & Channels
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10085, 'Paths and Files', 1202, 3,
  '{"template":"Class","required_nodes":["paths","files","path","method_invocation"]}',
  '["paths","files","path","nio"]', NULL),
(10086, 'FileChannel and ByteBuffer', 1202, 3,
  '{"template":"Class","required_nodes":["filechannel","bytebuffer","channel","method_invocation"]}',
  '["filechannel","bytebuffer","nio","channel"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 13: Date & Time (Modules: 1301, 1302) [6 items]
-- Core Time Types
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10087, 'LocalDate', 1301, 3,
  '{"template":"Class","required_nodes":["localdate","type_identifier"]}',
  '["localdate","java.time","date"]', NULL),
(10088, 'LocalDateTime', 1301, 3,
  '{"template":"Class","required_nodes":["localdatetime","type_identifier"]}',
  '["localdatetime","java.time","datetime"]', NULL),
(10089, 'Instant', 1301, 3,
  '{"template":"Class","required_nodes":["instant","type_identifier"]}',
  '["instant","java.time","timestamp"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Formatting & Duration
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10090, 'DateTimeFormatter', 1302, 3,
  '{"template":"Class","required_nodes":["datetimeformatter","format","parse","method_invocation"]}',
  '["datetimeformatter","format","parse","java.time.format"]', NULL),
(10091, 'ZonedDateTime and ZoneId', 1302, 3,
  '{"template":"Class","required_nodes":["zoneddatetime","zoneid","type_identifier"]}',
  '["zoneddatetime","zoneid","java.time"]', NULL),
(10092, 'Period and Duration', 1302, 3,
  '{"template":"Class","required_nodes":["period","duration","type_identifier"]}',
  '["period","duration","java.time"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 14: Annotations & Reflection (Modules: 1401, 1402) [6 items]
-- Annotations
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10093, '@Override and @Deprecated usage', 1401, 3,
  '{"template":"Class","required_nodes":["@override","@deprecated","annotation"]}',
  '["@override","@deprecated","annotation"]', NULL),
(10094, 'Custom annotation declaration', 1401, 3,
  '{"template":"Class","required_nodes":["annotation_declaration","@interface"]}',
  '["annotation","@interface","declaration"]', NULL),
(10095, 'Retention and Target', 1401, 3,
  '{"template":"Class","required_nodes":["retention","target","annotation"]}',
  '["retention","target","meta-annotation"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Reflection
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10096, 'Class.forName and ClassLoader', 1402, 3,
  '{"template":"Class","required_nodes":["class","forname","classloader","method_invocation"]}',
  '["class","forname","classloader","reflection"]', NULL),
(10097, 'getMethods and getFields', 1402, 3,
  '{"template":"Class","required_nodes":["getmethods","getfields","method_invocation"]}',
  '["getmethods","getfields","reflection"]', NULL),
(10098, 'Annotation introspection getAnnotation', 1402, 3,
  '{"template":"Class","required_nodes":["getannotation","method_invocation","annotation"]}',
  '["getannotation","annotation","reflection"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

-- Domain 15: Modules & Packaging (Modules: 1501, 1502) [2 items]
INSERT INTO knowledge_points (id, name, parent_id, level, ast_template, keywords, semantic_vec) VALUES
(10099, 'package declaration', 1501, 3,
  '{"template":"Class","required_nodes":["package_declaration"]}',
  '["package","declaration"]', NULL),
(10100, 'module-info requires', 1502, 3,
  '{"template":"Class","required_nodes":["module_declaration","requires"]}',
  '["module","requires","java.modules"]', NULL)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  parent_id=VALUES(parent_id),
  level=VALUES(level),
  ast_template=VALUES(ast_template),
  keywords=VALUES(keywords),
  semantic_vec=semantic_vec;

SET FOREIGN_KEY_CHECKS = 1;
