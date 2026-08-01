import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';

export default function AdminUsers() {
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const token = localStorage.getItem('token');
  const role = localStorage.getItem('role');
  
  // URL থেকে ?role=patient বা ?role=doctor পড়ার জন্য
  const [searchParams] = useSearchParams();
  const filterRole = searchParams.get('role');

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
        
        // যদি URL এ রোল থাকে, তবে শুধু সেই রোলের ইউজার ফিল্টার করে দেখাবে
        if (filterRole) {
          setUsers(response.data.filter(user => user.role === filterRole));
        } else {
          setUsers(response.data);
        }
      } catch (err) {
        console.error("Failed to fetch users", err);
      }
    };
    fetchUsers();
  }, [navigate, token, role, filterRole]);

  const handleToggleActive = async (userId, currentStatus) => {
    try {
      await axios.patch(`http://127.0.0.1:8000/api/auth/users/${userId}/`, 
        { is_active: !currentStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const response = await axios.get('http://127.0.0.1:8000/api/auth/users/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // আপডেট হওয়ার পরও যেন ফিল্টার ঠিক থাকে
      if (filterRole) {
        setUsers(response.data.filter(user => user.role === filterRole));
      } else {
        setUsers(response.data);
      }
    } catch (err) {
      alert("Failed to update user status.");
    }
  };

  // টাইটেল ডাইনামিকভাবে তৈরি করা (যেমন: Patient Management)
  const pageTitle = filterRole 
    ? `${filterRole.charAt(0).toUpperCase() + filterRole.slice(1)} Management` 
    : "User Management";

  return (
    <div className="min-h-screen bg-slate-50 text-gray-900 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        
        <div className="flex justify-between items-center mb-6">
          {/* টাইটেল এখানে পরিবর্তিত হবে */}
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            {pageTitle}
          </h1>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            Back to Dashboard
          </button>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <table className="w-full text-left">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                <th className="p-4 font-medium text-gray-500 text-sm">ID</th>
                <th className="p-4 font-medium text-gray-500 text-sm">Username</th>
                <th className="p-4 font-medium text-gray-500 text-sm">Role</th>
                <th className="p-4 font-medium text-gray-500 text-sm">Status</th>
                <th className="p-4 font-medium text-gray-500 text-sm text-center">Action</th>
              </tr>
            </thead>
            <tbody>
              {users.length > 0 ? (
                users.map((user) => (
                  <tr key={user.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-gray-400 font-mono text-sm">{user.id}</td>
                    <td className="p-4 font-medium text-gray-900">{user.username}</td>
                    <td className="p-4">
                      <span className="px-2.5 py-1 text-xs rounded-full bg-sky-50 text-sky-700 border border-sky-100 capitalize font-medium">
                        {user.role}
                      </span>
                    </td>
                    <td className="p-4">
                      {user.is_active ? (
                        <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-green-50 text-green-700 border border-green-100">
                          Active
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-red-50 text-red-700 border border-red-100">
                          Blocked
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-center">
                      <button
                        onClick={() => handleToggleActive(user.id, user.is_active)}
                        className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                          user.is_active 
                            ? 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-100' 
                            : 'bg-sky-500 text-white hover:bg-sky-600'
                        }`}
                      >
                        {user.is_active ? 'Block' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="p-8 text-center text-gray-500">No users found for this role.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  );
}