// 这是一个模拟的长文件 content
import java.io.*;

public class DataProcessor {
    // Snippet 1: 简单的Getter，不应该匹配 Try-Catch
    public String getName() {
        return "Processor";
    }

    // Snippet 2: 包含 Try-Catch 的 IO 操作，应该匹配
    public void processFile(String path) {
        System.out.println("Starting...");
        try {
            BufferedReader reader = new BufferedReader(new FileReader(path));
            String line = reader.readLine();
            while (line != null) {
                System.out.println(line);
                line = reader.readLine();
            }
        } catch (FileNotFoundException e) {
            System.err.println("File missing");
        } catch (IOException e) {
            e.printStackTrace();
        } finally {
            System.out.println("Done.");
        }
    }

    // Snippet 3: 复杂的逻辑但没有 Try-Catch
    public int calculate(int n) {
        if (n < 0) return 0;
        int sum = 0;
        for (int i=0; i<n; i++) {
            sum += i;
        }
        return sum;
    }
}
