import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  
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

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      alert("Please select an MRI image first.");
      return;
    }

    setUploading(true);
    setUploadStatus('');

    const formData = new FormData();
    formData.append('original_image', file);

    try {
      await axios.post('http://127.0.0.1:8000/api/scans/analyze/', formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      setUploadStatus('Scan uploaded successfully! AI is processing it.');
      setFile(null); 
    } catch (err) {
      setUploadStatus('Failed to upload scan. Please try again.');
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-gray-900 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        
        {/* Header Section */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">Welcome, {username}!</h1>
            <p className="text-gray-500 mt-1 text-sm">Role: <span className="capitalize text-sky-600 font-semibold border border-sky-100 bg-sky-50 px-2 py-0.5 rounded-full text-xs">{role}</span></p>
          </div>
          
          <div className="flex space-x-3">
            {(role === 'admin' || role === 'super_admin') && (
              <button
                onClick={() => navigate('/admin/users')}
                className="px-4 py-2 font-medium text-white bg-sky-500 rounded-md hover:bg-sky-600 transition-colors"
              >
                Manage Users
              </button>
            )}
            
            <button
              onClick={handleLogout}
              className="px-4 py-2 font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Admin Stats Section */}
        {(role === 'admin' || role === 'super_admin') && (
          <div className="mt-8">
            <h2 className="text-lg font-semibold text-gray-700 mb-4">System Overview</h2>
            
            {stats ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                
                {/* Total Patients কার্ডে ক্লিক করলে শুধু পেশেন্ট দেখাবে */}
                <div 
                  onClick={() => navigate('/admin/users?role=patient')} 
                  className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer"
                >
                  <h3 className="text-gray-500 text-sm font-medium">Total Patients</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_patients}</p>
                </div>

                {/* Total Scans কার্ডে ক্লিক করলে সব স্ক্যান দেখাবে */}
                <div 
                  onClick={() => navigate('/admin/scans?status=all')} 
                  className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer"
                >
                  <h3 className="text-gray-500 text-sm font-medium">Total Scans</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_scans}</p>
                </div>

                {/* Pending Reviews কার্ডে ক্লিক করলে শুধু পেন্ডিং স্ক্যান দেখাবে */}
                <div 
                  onClick={() => navigate('/admin/scans?status=pending')} 
                  className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer"
                >
                  <h3 className="text-gray-500 text-sm font-medium">Pending Reviews</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.pending_reviews}</p>
                </div>

                {/* Total Radiologists কার্ডে ক্লিক করলে শুধু রেডিওলজিস্ট দেখাবে */}
                <div 
                  onClick={() => navigate('/admin/users?role=radiologist')} 
                  className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer"
                >
                  <h3 className="text-gray-500 text-sm font-medium">Total Radiologists</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_radiologists}</p>
                </div>

                {/* Total Doctors কার্ডে ক্লিক করলে শুধু ডাক্তার দেখাবে */}
                <div 
                  onClick={() => navigate('/admin/users?role=doctor')} 
                  className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer"
                >
                  <h3 className="text-gray-500 text-sm font-medium">Total Doctors</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_doctors}</p>
                </div>

                {/* Approved Reports কার্ডে ক্লিক করলে শুধু অ্যাপ্রুভড রিপোর্ট দেখাবে */}
                <div 
                  onClick={() => navigate('/admin/scans?status=approved')} 
                  className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer"
                >
                  <h3 className="text-gray-500 text-sm font-medium">Approved Reports</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.approved_reports}</p>
                </div>

              </div>
            ) : (
              <p className="text-gray-400">Loading stats...</p>
            )}
          </div>
        )}

        {/* Patient Upload Section */}
        {role === 'patient' && (
          <div className="mt-8">
            <h2 className="text-lg font-semibold text-gray-700 mb-4">Upload New MRI Scan</h2>
            <div className="p-8 bg-white rounded-lg border border-gray-200 shadow-sm">
              <form onSubmit={handleUpload} className="space-y-5">
                <div className="flex flex-col items-center justify-center w-full">
                  <label htmlFor="dropzone-file" className="flex flex-col items-center justify-center w-full h-44 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <svg className="w-10 h-10 mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                      <p className="mb-2 text-sm text-gray-500"><span className="font-semibold text-sky-600">Click to upload</span> or drag and drop</p>
                      <p className="text-xs text-gray-400">JPG, PNG up to 10MB</p>
                    </div>
                    <input id="dropzone-file" type="file" className="hidden" onChange={handleFileChange} accept="image/*" />
                  </label>
                </div>
                
                {file && (
                  <p className="text-sm text-gray-600 text-center">Selected file: <span className="font-medium text-sky-600">{file.name}</span></p>
                )}

                {uploadStatus && (
                  <div className={`p-3 text-sm rounded-md text-center ${uploadStatus.includes('successfully') ? 'bg-green-50 text-green-700 border border-green-100' : 'bg-red-50 text-red-700 border border-red-100'}`}>
                    {uploadStatus}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={uploading || !file}
                  className="w-full px-4 py-3 font-semibold text-white bg-sky-500 rounded-md hover:bg-sky-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500 disabled:bg-sky-300 transition-colors"
                >
                  {uploading ? 'Uploading & Analyzing...' : 'Upload & Analyze'}
                </button>
              </form>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}