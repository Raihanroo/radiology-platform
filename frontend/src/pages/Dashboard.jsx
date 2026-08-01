import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  
  const username = localStorage.getItem('username');
  const role = localStorage.getItem('role');
  const token = localStorage.getItem('token');

  useEffect(() => {
    if (!token) {
      navigate('/');
      return;
    }

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
    <div className="min-h-screen bg-gray-100 text-gray-900 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        
        {/* Header Section */}
        <div className="flex justify-between items-center mb-10 border-b border-gray-200 pb-4">
          <div>
            <h1 className="text-3xl font-light tracking-wider uppercase">Welcome, {username}!</h1>
            <p className="text-gray-500 mt-1">Role: <span className="capitalize text-black font-medium border border-gray-300 px-2 py-0.5 rounded-full text-xs">{role}</span></p>
          </div>
          
          <div className="flex space-x-4">
            {(role === 'admin' || role === 'super_admin') && (
              <button
                onClick={() => navigate('/admin/users')}
                className="px-5 py-2 font-medium text-white bg-black rounded-md hover:bg-gray-800 transition-colors"
              >
                Manage Users
              </button>
            )}
            
            <button
              onClick={handleLogout}
              className="px-5 py-2 font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Stats Section */}
        {(role === 'admin' || role === 'super_admin') && (
          <div className="mt-8">
            <h2 className="text-xl font-light tracking-wider uppercase text-gray-500 mb-6">System Overview</h2>
            
            {stats ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                  <h3 className="text-gray-500 text-xs font-medium uppercase tracking-wider">Total Patients</h3>
                  <p className="text-5xl font-light text-black mt-3">{stats.total_patients}</p>
                </div>

                <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                  <h3 className="text-gray-500 text-xs font-medium uppercase tracking-wider">Total Scans</h3>
                  <p className="text-5xl font-light text-black mt-3">{stats.total_scans}</p>
                </div>

                <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                  <h3 className="text-gray-500 text-xs font-medium uppercase tracking-wider">Pending Reviews</h3>
                  <p className="text-5xl font-light text-black mt-3">{stats.pending_reviews}</p>
                </div>

                <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                  <h3 className="text-gray-500 text-xs font-medium uppercase tracking-wider">Total Radiologists</h3>
                  <p className="text-5xl font-light text-black mt-3">{stats.total_radiologists}</p>
                </div>

                <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                  <h3 className="text-gray-500 text-xs font-medium uppercase tracking-wider">Total Doctors</h3>
                  <p className="text-5xl font-light text-black mt-3">{stats.total_doctors}</p>
                </div>

                <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                  <h3 className="text-gray-500 text-xs font-medium uppercase tracking-wider">Approved Reports</h3>
                  <p className="text-5xl font-light text-black mt-3">{stats.approved_reports}</p>
                </div>

              </div>
            ) : (
              <p className="text-gray-400">Loading stats...</p>
            )}
          </div>
        )}

        {role !== 'admin' && role !== 'super_admin' && (
           <div className="p-6 bg-white rounded-md border border-gray-200 shadow-sm">
             <p className="text-gray-600">আপনার ড্যাশবোর্ডে আপনার স্ক্যান ও রিপোর্টের তালিকা দেখা যাবে। (Coming Soon)</p>
           </div>
        )}

      </div>
    </div>
  );
}