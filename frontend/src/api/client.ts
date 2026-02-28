/**
 * Axios 实例配置
 * 统一处理请求/响应拦截
 */

import axios from 'axios';
import type { AxiosError, AxiosResponse } from 'axios';

// 内联定义避免模块解析问题
interface ApiErrorResponse {
  code: number;
  message: string;
  error?: string;
}

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截器
client.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<ApiErrorResponse>) => {
    const status = error.response?.status;
    const errorData = error.response?.data;

    // 400/404/422: 业务错误，展示给用户
    if (status && [400, 404, 422].includes(status)) {
      const message = errorData?.message || errorData?.error || '请求失败';
      return Promise.reject(new Error(message));
    }

    // 500+: 服务器错误，仅记录控制台
    if (status && status >= 500) {
      console.error('[API Error]', error.response?.data);
      return Promise.reject(new Error('服务器内部错误，请稍后重试'));
    }

    // 网络错误
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('请求超时，请检查网络连接'));
    }

    return Promise.reject(new Error('网络连接失败'));
  }
);

export default client;
