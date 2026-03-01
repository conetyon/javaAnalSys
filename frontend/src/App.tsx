/**
 * Root Component
 * Configures routing, auth provider, and global styles
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider, Layout } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { AuthProvider } from './contexts/AuthContext';
import Header from './components/Header';
import PrivateRoute from './components/PrivateRoute';
import Dashboard from './pages/Dashboard';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import HistoryPage from './pages/HistoryPage';
import FavoritesPage from './pages/FavoritesPage';

const { Content } = Layout;

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Auth pages (no header) */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Main app layout with header */}
            <Route
              path="/*"
              element={
                <Layout style={{ minHeight: '100vh' }}>
                  <Header />
                  <Content>
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/history" element={<PrivateRoute><HistoryPage /></PrivateRoute>} />
                      <Route path="/favorites" element={<PrivateRoute><FavoritesPage /></PrivateRoute>} />
                    </Routes>
                  </Content>
                </Layout>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ConfigProvider>
  );
}

export default App;
