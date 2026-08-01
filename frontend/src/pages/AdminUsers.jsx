
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function AdminUsers() {
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');

  useEffect(() => {
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
      const response = await axios.get('http://127.0.0.1:8000/api/auth/users/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUsers(response.data);
    } catch (err) {
      alert("Failed to update user status.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 text-gray-900 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        
        <div className="flex justify-between items-center mb-10 border-b border-gray-200 pb-4">
          <h1 className="text-3xl font-light tracking-wider uppercase">User Management</h1>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-5 py-2 font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            Back to Dashboard
          </button>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm">
          <table className="w-full text-left">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="p-5 font-medium text-gray-500 text-xs uppercase tracking-wider">ID</th>
                <th className="p-5 font-medium text-gray-500 text-xs uppercase tracking-wider">Username</th>
                <th className="p-5 font-medium text-gray-500 text-xs uppercase tracking-wider">Role</th>
                <th className="p-5 font-medium text-gray-500 text-xs uppercase tracking-wider">Status</th>
                <th className="p-5 font-medium text-gray-500 text-xs uppercase tracking-wider text-center">Action</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors">
                  <td className="p-5 text-gray-400 font-mono">{user.id}</td>
                  <td className="p-5 font-medium text-gray-900 text-lg">{user.username}</td>
                  <td className="p-5">
                    <span className="px-3 py-1 text-xs rounded-full bg-gray-100 text-gray-700 border border-gray-200 capitalize">
                      {user.role}
                    </span>
                  </td>
                  <td className="p-5">
                    {user.is_active ? (
                      <span className="px-3 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-700 border border-green-200">
                        Active
                      </span>
                    ) : (
                      <span className="px-3 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-700 border border-red-200">
                        Blocked
                      </span>
                    )}
                  </td>
                  <td className="p-5 text-center">
                    <button
                      onClick={() => handleToggleActive(user.id, user.is_active)}
                      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                        user.is_active 
                          ? 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-100' 
                          : 'bg-black text-white hover:bg-gray-800'
                      }`}
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