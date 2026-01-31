// sample_code.java
// 扩展的示例文件，覆盖更多Java知识点
package demo;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.sql.*;
import java.util.*;
import java.util.concurrent.locks.*;
import java.util.stream.*;

public class DataProcessor {

    // Snippet 1: 简单 Getter，展示基本方法和String类型
    public String getName() {
        return "Processor";
    }

    // Snippet 2: Try-Catch + While循环 + IO操作，命中多个KP
    public void processFile(String path) {
        System.out.println("Starting IO...");
        try {
            BufferedReader reader = new BufferedReader(new FileReader(path));
            String line = reader.readLine();
            while (line != null) {
                System.out.println(line);
                line = reader.readLine();
            }
            reader.close();
        } catch (FileNotFoundException e) {
            System.err.println("File missing");
        } catch (IOException e) {
            e.printStackTrace();
        } finally {
            System.out.println("IO Done.");
        }
    }

    // Snippet 3: For循环 + If-Else + 基本类型（int）
    public int calculate(int n) {
        if (n < 0) return 0;
        int sum = 0;
        for (int i = 0; i < n; i++) {
            sum += i;
        }
        return sum;
    }

    // Snippet 4: Try-with-resources + Paths.get + Files.readAllLines
    public List<String> readWithNIO(String path) {
        try {
            Path p = Paths.get(path);
            return Files.readAllLines(p, StandardCharsets.UTF_8);
        } catch (IOException e) {
            e.printStackTrace();
            return Collections.emptyList();
        }
    }

    // Snippet 5: ArrayList使用 + While循环 + String操作 + Try-Catch
    public List<String> filterLines(String path) {
        List<String> result = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(new FileReader(path))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.length() > 0) {
                    result.add(line.trim());
                }
            }
        } catch (IOException e) {
            System.err.println("Error: " + e.getMessage());
        }
        return result;
    }

    // Snippet 6: HashSet使用 + For循环
    public Set<String> uniqueWords(String[] words) {
        Set<String> unique = new HashSet<>();
        for (String word : words) {
            unique.add(word.toLowerCase());
        }
        System.out.println("Unique count: " + unique.size());
        return unique;
    }

    // Snippet 7: HashMap使用 + For循环
    public Map<String, Integer> countWords(String[] words) {
        Map<String, Integer> counts = new HashMap<>();
        for (String word : words) {
            counts.put(word, counts.getOrDefault(word, 0) + 1);
        }
        return counts;
    }

    // Snippet 8: Files工具类 + Try-Catch
    public void writeLines(String path, List<String> lines) {
        try {
            Path p = Paths.get(path);
            Files.write(p, lines, StandardCharsets.UTF_8);
            System.out.println("Written " + lines.size() + " lines");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    // Snippet 9: 基本类型运算 + If-Else
    public boolean isPrime(int num) {
        if (num <= 1) {
            return false;
        }
        for (int i = 2; i * i <= num; i++) {
            if (num % i == 0) {
                return false;
            }
        }
        return true;
    }

    // Snippet 10: Try-with-resources + JDBC + While循环 + Collections
    public List<String> queryUsers(String url, String user, String password) {
        List<String> users = new ArrayList<>();
        String sql = "SELECT id, name FROM users WHERE state = ?";
        try (Connection conn = DriverManager.getConnection(url, user, password);
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, "ACTIVE");
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    users.add(rs.getString("name"));
                }
            }
        } catch (SQLException e) {
            e.printStackTrace();
        }
        return users;
    }
}

// Snippet 11: 构造器示例
class Product {
    private String name;
    private double price;
    private int quantity;

    // 默认构造器
    public Product() {
        this.name = "Unknown";
        this.price = 0.0;
        this.quantity = 0;
    }

    // 带参数的构造器
    public Product(String name, double price) {
        this.name = name;
        this.price = price;
        this.quantity = 1;
    }

    // 完整构造器
    public Product(String name, double price, int quantity) {
        this.name = name;
        this.price = price;
        this.quantity = quantity;
    }

    public double getTotalPrice() {
        return price * quantity;
    }
}

// Snippet 12: Break和Continue示例
class LoopControlDemo {
    public List<Integer> findPrimesUnder(int max) {
        List<Integer> primes = new ArrayList<>();
        for (int num = 2; num < max; num++) {
            if (num > 100) {
                break; // 超过100就停止
            }
            boolean isPrime = true;
            for (int i = 2; i * i <= num; i++) {
                if (num % i == 0) {
                    isPrime = false;
                    break;
                }
            }
            if (!isPrime) {
                continue; // 跳过非质数
            }
            primes.add(num);
        }
        return primes;
    }

    public int sumEvenNumbers(int[] numbers) {
        int sum = 0;
        for (int num : numbers) {
            if (num % 2 != 0) {
                continue; // 跳过奇数
            }
            sum += num;
        }
        return sum;
    }
}

// Snippet 13: Lambda表达式示例
class LambdaDemo {
    public List<String> filterAndSort(List<String> items) {
        return items.stream()
                .filter(s -> s.length() > 3)  // Lambda过滤
                .sorted((a, b) -> a.compareTo(b))  // Lambda排序
                .collect(Collectors.toList());
    }

    public void processItems(List<String> items) {
        items.forEach(item -> System.out.println(item));  // Lambda遍历
    }

    public Map<Integer, List<String>> groupByLength(List<String> words) {
        return words.stream()
                .collect(Collectors.groupingBy(s -> s.length()));  // Lambda分组
    }
}

// Snippet 14: Stream Pipeline示例
class StreamDemo {
    public double calculateAverage(List<Integer> numbers) {
        return numbers.stream()
                .filter(n -> n > 0)
                .mapToInt(Integer::intValue)
                .average()
                .orElse(0.0);
    }

    public List<String> processStrings(List<String> input) {
        return input.stream()
                .filter(Objects::nonNull)
                .map(String::trim)
                .map(String::toUpperCase)
                .distinct()
                .sorted()
                .collect(Collectors.toList());
    }

    public long countWords(String text) {
        return Arrays.stream(text.split("\\s+"))
                .filter(s -> !s.isEmpty())
                .count();
    }
}

// Snippet 15: 字符串操作示例
class StringOperations {
    public String processText(String input) {
        if (input == null || input.isEmpty()) {
            return "";
        }

        // 各种字符串操作
        String trimmed = input.trim();
        String upper = trimmed.toUpperCase();
        String sub = upper.substring(0, Math.min(10, upper.length()));

        int index = sub.indexOf("A");
        int length = sub.length();
        char first = sub.charAt(0);

        return sub + " [len=" + length + ", idx=" + index + ", first=" + first + "]";
    }

    public boolean validateInput(String text) {
        return text != null &&
               !text.isEmpty() &&
               text.length() >= 3 &&
               text.matches("[a-zA-Z0-9]+");
    }
}

// Snippet 16: Synchronized同步示例
class SynchronizedDemo {
    private int counter = 0;

    public synchronized void increment() {
        counter++;
    }

    public void syncBlock() {
        synchronized (this) {
            counter += 10;
        }
    }

    public synchronized int getCounter() {
        return counter;
    }
}

// Snippet 17: ReentrantLock示例
class LockDemo {
    private final Lock lock = new ReentrantLock();
    private int value = 0;

    public void updateValue(int delta) {
        lock.lock();
        try {
            value += delta;
            System.out.println("Updated to: " + value);
        } finally {
            lock.unlock();
        }
    }

    public boolean tryUpdate(int delta) {
        if (lock.tryLock()) {
            try {
                value += delta;
                return true;
            } finally {
                lock.unlock();
            }
        }
        return false;
    }
}

// Snippet 18: Enum枚举示例
enum OrderStatus {
    PENDING,
    PROCESSING,
    SHIPPED,
    DELIVERED,
    CANCELLED;

    public boolean isFinal() {
        return this == DELIVERED || this == CANCELLED;
    }
}

class Order {
    private String id;
    private OrderStatus status;

    public Order(String id) {
        this.id = id;
        this.status = OrderStatus.PENDING;
    }

    public void updateStatus(OrderStatus newStatus) {
        if (!status.isFinal()) {
            status = newStatus;
            System.out.println("Order " + id + " is now " + status);
        }
    }
}

// Snippet 19: 基本类型综合示例
class PrimitiveTypesDemo {
    public void demonstrateTypes() {
        // 整数类型
        byte b = 127;
        short s = 32000;
        int i = 1000000;
        long l = 999999999L;

        // 浮点类型
        float f = 3.14f;
        double d = 2.718281828;

        // 字符和布尔
        char c = 'A';
        boolean flag = true;

        // 运算
        int sum = i + s;
        double result = d * f;
        boolean check = (sum > 0) && flag;

        System.out.println("Sum: " + sum + ", Result: " + result + ", Check: " + check);
    }
}

// Snippet 20: Try-Catch多异常处理
class ExceptionHandlingDemo {
    public String readFileContent(String path) {
        StringBuilder content = new StringBuilder();
        try {
            List<String> lines = Files.readAllLines(Paths.get(path));
            for (String line : lines) {
                content.append(line).append("\n");
            }
        } catch (FileNotFoundException e) {
            System.err.println("File not found: " + path);
        } catch (IOException e) {
            System.err.println("IO error: " + e.getMessage());
            e.printStackTrace();
        } catch (Exception e) {
            System.err.println("Unexpected error");
        }
        return content.toString();
    }
}
