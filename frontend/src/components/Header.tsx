/**
 * Header Component
 *
 * Top navigation bar with user menu.
 * Shows login button for anonymous users, dropdown menu for authenticated users.
 * Includes quota indicator for AI explanation feature.
 */

import { useNavigate } from 'react-router-dom';
import { Layout, Button, Dropdown, Avatar, Space, Typography, Divider } from 'antd';
import { UserOutlined, LogoutOutlined, LoginOutlined, HistoryOutlined, StarOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import QuotaIndicator from './QuotaIndicator';
import type { MenuProps } from 'antd';

const { Header: AntHeader } = Layout;
const { Text } = Typography;

export default function Header() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  // User dropdown menu items
  const menuItems: MenuProps['items'] = [
    {
      key: 'user-info',
      label: (
        <Space direction="vertical" size={0}>
          <Text strong>{user?.username}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{user?.role}</Text>
        </Space>
      ),
      disabled: true,
    },
    { type: 'divider' },
    {
      key: 'history',
      icon: <HistoryOutlined />,
      label: 'Match History',
      onClick: () => navigate('/history'),
    },
    {
      key: 'favorites',
      icon: <StarOutlined />,
      label: 'Favorites',
      onClick: () => navigate('/favorites'),
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Sign Out',
      onClick: handleLogout,
    },
  ];

  return (
    <AntHeader style={{
      background: '#fff',
      padding: '0 24px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      borderBottom: '1px solid #f0f0f0',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      <div
        style={{ cursor: 'pointer' }}
        onClick={() => navigate('/')}
      >
        <Text strong style={{ fontSize: 18 }}>
          Java Knowledge Matching
        </Text>
      </div>

      <div>
        {isAuthenticated ? (
          <Space split={<Divider type="vertical" />}>
            {/* 配额指示器 */}
            <QuotaIndicator compact />

            {/* 用户菜单 */}
            <Dropdown menu={{ items: menuItems }} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <Text>{user?.username}</Text>
              </Space>
            </Dropdown>
          </Space>
        ) : (
          <Space>
            <Button
              type="text"
              icon={<LoginOutlined />}
              onClick={() => navigate('/login')}
            >
              Sign In
            </Button>
            <Button
              type="primary"
              onClick={() => navigate('/register')}
            >
              Register
            </Button>
          </Space>
        )}
      </div>
    </AntHeader>
  );
}
