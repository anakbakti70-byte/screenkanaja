import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

interface User {
  id: string;
  username: string;
  role: string;
  avatar_url?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string, userData?: User) => Promise<void>;
  logout: () => void;
  updateUser: (user: User) => void;
  isAuthenticated: boolean;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // Configure axios defaults when token changes
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // Set up global 401 interceptor
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (axios.isAxiosError(error) && error.response?.status === 401) {
          console.warn("Session expired. Logging out.");
          logout();
        }
        return Promise.reject(error);
      }
    );
    return () => axios.interceptors.response.eject(interceptor);
  }, []);

  useEffect(() => {
    const fetchUser = async () => {
      if (token) {
        try {
          // Add timeout to prevent permanent "Loading..."
          const res = await axios.get('/api/users/me', {
            headers: { Authorization: `Bearer ${token}` },
            timeout: 5000 // 5 seconds timeout
          });
          setUser(res.data);
        } catch (error) {
          console.error("Failed to fetch user:", error);
          // If it's a 401, token is definitely bad
          if (axios.isAxiosError(error) && error.response?.status === 401) {
            setToken(null);
            localStorage.removeItem('token');
          }
        }
      }
      setLoading(false);
    };

    fetchUser();
  }, [token]);

  const login = async (newToken: string) => {
    setToken(newToken);
    localStorage.setItem('token', newToken);
    
    // Fetch user info immediately after login
    try {
      const res = await axios.get('/api/users/me', {
        headers: { Authorization: `Bearer ${newToken}` }
      });
      setUser(res.data);
    } catch(err) {
      console.error(err);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  const updateUser = (updated: User) => {
    setUser(updated);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, updateUser, isAuthenticated: !!token, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
