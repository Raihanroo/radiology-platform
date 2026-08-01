import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  
  const username = localStorage.getItem('username');
  const role = localStorage.getItem('role');
  const token = localStorage.getItem('token');

  // যদি ইউজার লগইন না করা থাকে, তবে লগইন পেজে ফেরত পাঠানো
  useEffect(() => {
    if (!token) {
      navigate('/');
      return;
    }

    // শুধুমাত্র Admin বা Super Admin হলে stats আনবে
    if (role === 'admin' || role === 'super_admin') {
      const fetchStats = async () => {
        try {
          const response = await axios.get('http://127.0.0.1:8000/api/scans/admin-stats/', {
            headers: { Authorization: `Bearer ${token}` }
          });
          setStats(response.data);
        } catch (err) {
          console.error("Failed to fetch stats", err);
        }
      };
      fetchStats();
    }
  }, [navigate, token, role]);

  const handleLogout = () => {
    localStorage.clear();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        
        {/* Header Section */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">Welcome, {username}!</h1>
            <p className="text-gray-400">Role: <span className="capitalize text-blue-400 font-semibold">{role}</span></p>
          </div>
          
          {/* বাটনগুলোর কন্টেইনার */}
          <div className="flex space-x-4">
            {/* অ্যাডমিন হলেই শুধু এই বাটনটি দেখাবে */}
            {(role === 'admin' || role === 'super_admin') && (
              <button
                onClick={() => navigate('/admin/users')}
                className="px-4 py-2 font-semibold text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
              >
                Manage Users
              </button>
            )}
            
            <button
              onClick={handleLogout}
              className="px-4 py-2 font-semibold text-white bg-red-600 rounded-md hover:bg-red-700 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Stats Section (শুধু Admin দেখবে) */}
        {(role === 'admin' || role === 'super_admin') && (
          <div className="mt-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-300">System Overview</h2>
            
            {stats ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                <div className="p-6 bg-gray-800 rounded-lg border border-gray-700 shadow-sm">
                  <h3 className="text-gray-400 text-sm font-medium uppercase">Total Patients</h3>
                  <p className="text-4xl font-bold text-blue-400 mt-2">{stats.total_patients}</p>
                </div>

                <div className="p-6 bg-gray-800 rounded-lg border border-gray-700 shadow-sm">
                  <h3 className="text-gray-400 text-sm font-medium uppercase">Total Scans</h3>
                  <p className="text-4xl font-bold text-green-400 mt-2">{stats.total_scans}</p>
                </div>

                <div className="p-6 bg-gray-800 rounded-lg border border-gray-700 shadow-sm">
                  <h3 className="text-gray-400 text-sm font-medium uppercase">Pending Reviews</h3>
                  <p className="text-4xl font-bold text-yellow-400 mt-2">{stats.pending_reviews}</p>
                </div>

                <div className="p-6 bg-gray-800 rounded-lg border border-gray-700 shadow-sm">
                  <h3 className="text-gray-400 text-sm font-medium uppercase">Total Radiologists</h3>
                  <p className="text-4xl font-bold text-purple-400 mt-2">{stats.total_radiologists}</p>
                </div>

                <div className="p-6 bg-gray-800 rounded-lg border border-gray-700 shadow-sm">
                  <h3 className="text-gray-400 text-sm font-medium uppercase">Total Doctors</h3>
                  <p className="text-4xl font-bold text-pink-400 mt-2">{stats.total_doctors}</p>
                </div>

                <div className="p-6 bg-gray-800 rounded-lg border border-gray-700 shadow-sm">
                  <h3 className="text-gray-400 text-sm font-medium uppercase">Approved Reports</h3>
                  <p className="text-4xl font-bold text-teal-400 mt-2">{stats.approved_reports}</p>
                </div>

              </div>
            ) : (
              <p className="text-gray-400">Loading stats...</p>
            )}
          </div>
        )}

        {/* Other Roles (Patient/Doctor/Radiologist) এর জন্য পরবর্তীতে কোড বসব */}
        {role !== 'admin' && role !== 'super_admin' && (
           <div className="p-6 bg-gray-800 rounded-md border border-gray-700">
             <p className="text-gray-300">আপনার ড্যাশবোর্ডে আপনার স্ক্যান ও রিপোর্টের তালিকা দেখা যাবে। (Coming Soon)</p>
           </div>
        )}

      </div>
    </div>
  );
}