/**
 * Authentication Service (Node.js/Express)
 * 监听 8070 端口，提供简单的用户凭证验证功能。
 * Auth logic is hardcoded for demonstration purposes.
 */
const express = require('express');
const app = express();

// **修复：设置主机为 0.0.0.0 确保在 Docker 容器中可从外部访问**
const HOST = '0.0.0.0';
const PORT = 8070; // 端口更新为 8070

// 硬编码的测试用户凭证 (用于演示目的)
const MOCK_USER = 'test';
const MOCK_PASSWORD = '123';

// 使用 JSON 解析中间件，处理 POST 请求体
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

/**
 * POST /authenticate
 * 接收 username 和 password，进行验证。
 */
app.post('/authenticate', (req, res) => {
    // 从请求体中解构 username 和 password
    const { username, password } = req.body;
    
    // 检查是否提供了凭证
    if (!username || !password) {
        return res.status(400).json({
            message: 'Missing username or password.',
            authenticated: false
        });
    }

    // 模拟验证逻辑
    if (username === MOCK_USER && password === MOCK_PASSWORD) {
        console.log(`[AUTH] User ${username} successfully authenticated.`);
        
        // 验证成功：返回 200 OK
        return res.status(200).json({
            message: 'Authentication successful',
            authenticated: true,
            user_id: username,
            // 生产环境中这里会生成一个 JWT 或会话ID
            mock_token: `MOCK_TOKEN_${Date.now()}` 
        });
    } else {
        console.warn(`[AUTH] Failed attempt for user: ${username}`);
        
        // 验证失败：返回 401 Unauthorized
        return res.status(401).json({
            message: 'Invalid credentials',
            authenticated: false
        });
    }
});

// 根路径，用于健康检查
app.get('/', (req, res) => {
    res.status(200).send('Authentication Service is running.');
});

// 启动服务器
// **关键改动：将 HOST 变量 (0.0.0.0) 传递给 listen 函数**
app.listen(PORT, HOST, () => {
    console.log(`Authentication Service listening on ${HOST}:${PORT}`);
    console.log(`Test with: POST http://localhost:${PORT}/authenticate`);
});
