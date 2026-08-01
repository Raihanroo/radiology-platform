import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function AdminUsers() {
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');

  useEffect(() => {
    // যদি অ্যাডমিন না হয়, তবে ড্যাশবোর্ডে ফেরত পাঠানো
    if (!token || (role !== 'admin' && role !== 'super_admin')) {
      navigate('/dashboard');
      return;
    }

    const fetchUsers = async () => {
      try {
        const response = await axios.get('http://127.0.0.1:8000/api/auth/users/', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setUsers(response.data);
      } catch (err) {
        console.error("Failed to fetch users", err);
      }
    };
    fetchUsers();
  }, [navigate, token, role]);

  const handleToggleActive = async (userId, currentStatus) => {
    try {
      await axios.patch(`http://127.0.0.1:8000/api/auth/users/${userId}/`, 
        { is_active: !currentStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      // আপডেট হওয়ার পর লিস্টটি রিফ্রেশ করার জন্য আবার ইউজার আনছি
      const response = await axios.get('http://127.0.0.1:8000/api/auth/users/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUsers(response.data);
    } catch (err) {
      alert("Failed to update user status.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">User Management</h1>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 font-semibold text-white bg-gray-600 rounded-md hover:bg-gray-700 transition-colors"
          >
            Back to Dashboard
          </button>
        </div>

        <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
          <table className="w-full text-left">
            <thead className="border-b border-gray-700 bg-gray-700/50">
              <tr>
                <th className="p-4 font-medium text-gray-300">ID</th>
                <th className="p-4 font-medium text-gray-300">Username</th>
                <th className="p-4 font-medium text-gray-300">Role</th>
                <th className="p-4 font-medium text-gray-300">Status</th>
                <th className="p-4 font-medium text-gray-300 text-center">Action</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-gray-700 last:border-0">
                  <td className="p-4 text-gray-400">{user.id}</td>
                  <td className="p-4 font-semibold">{user.username}</td>
                  <td className="p-4">
                    <span className="px-2 py-1 text-xs rounded-full bg-blue-900/50 text-blue-300 capitalize">
                      {user.role}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className={`px-2 py-1 text-xs rounded-full ${user.is_active ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'}`}>
                      {user.is_active ? 'Active' : 'Blocked'}
                    </span>
                  </td>
                  <td className="p-4 text-center">
                    <button
                      onClick={() => handleToggleActive(user.id, user.is_active)}
                      className={`px-3 py-1 text-sm font-semibold rounded-md ${user.is_active ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}`}
                    >
                      {user.is_active ? 'Block' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  );
}