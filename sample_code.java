// sample_code.java
// 这是一个覆盖面更广的示例文件 content
package demo;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.sql.*;
import java.util.*;
import java.util.concurrent.locks.*;
import java.util.stream.*;

public class DataProcessor {

    // Snippet 1: 简单 Getter，不匹配 Try-Catch
    public String getName() {
        return "Processor";
    }

    // Snippet 2: Try-Catch 的 IO 操作，应该命中 Try-Catch IO
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

    // Snippet 3: 仅逻辑，不应命中任何异常相关 KP
    public int calculate(int n) {
        if (n < 0) return 0;
        int sum = 0;
        for (int i = 0; i < n; i++) {
            sum += i;
        }
        return sum;
    }

    // Snippet 4: 声明 throws，应该命中异常抛出与传播
    public void riskyOperation() throws IOException {
        if (System.currentTimeMillis() % 2 == 0) {
            throw new IOException("boom");
        }
    }

    // Snippet 5: Java NIO 文件操作，应该命中 NIO
    public List<String> readWithNIO(String path) {
        try {
            Path p = Paths.get(path);
            return Files.readAllLines(p, StandardCharsets.UTF_8);
        } catch (IOException e) {
            e.printStackTrace();
            return Collections.emptyList();
        }
    }

    // Snippet 6: Stream API 使用，应该命中 Stream API
    public List<String> transform(List<String> input) {
        return input.stream()
                .filter(Objects::nonNull)
                .map(String::trim)
                .map(String::toUpperCase)
                .collect(Collectors.toList());
    }

    // Snippet 7: synchronized 同步块，应该命中同步与并发
    private int counter = 0;
    public void syncIncrement() {
        synchronized (this) {
            counter++;
        }
    }

    // Snippet 8: ReentrantLock 使用，应该命中同步与并发
    private final Lock lock = new ReentrantLock();
    public void lockedIncrement() {
        lock.lock();
        try {
            counter++;
        } finally {
            lock.unlock();
        }
    }

    // Snippet 9: wait/notify 示例（仅演示）
    public synchronized void waitNotifyDemo() {
        try {
            wait(5);
            notifyAll();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}

class DatabaseDemo {
    // Snippet 10: JDBC 查询与资源管理，应命中 JDBC KP
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
