import { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post('http://127.0.0.1:8000/api/auth/login/', {
        username: username,
        password: password
      });

      localStorage.setItem('token', response.data.access);
      localStorage.setItem('role', response.data.user.role);
      localStorage.setItem('username', response.data.user.username);

      navigate('/dashboard');
      
    } catch (err) {
      setError('Invalid username or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex w-full h-screen items-center justify-center bg-slate-50 text-gray-900 p-4">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-xl shadow-lg border border-gray-100">
        <div className="text-center">
          {/* লোগো এবং প্ল্যাটফর্মের নাম */}
          <div className="flex flex-col items-center justify-center mb-4">
            <img src="/logo.png" alt="Logo" className="h-20 w-20 object-contain mb-3" />
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">AI Assisted Radiology Platform</h1>
          </div>
          <p className="mt-2 text-sm text-gray-500">Please login to your account</p>
        </div>
        
        {error && (
          <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-100 rounded-md">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700">Username</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 mt-1 bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 placeholder-gray-400 transition-colors"
              placeholder="Enter your username"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 mt-1 bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 placeholder-gray-400 transition-colors"
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-3 font-semibold text-white bg-sky-500 rounded-md hover:bg-sky-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500 disabled:bg-sky-300 transition-colors"
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        
        <p className="text-sm text-center text-gray-500">
          Don't have an account? <Link to="/register" className="text-sky-600 hover:underline font-medium">Register</Link>
        </p>
      </div>
    </div>
  );
}