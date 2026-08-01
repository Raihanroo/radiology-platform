import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [myScans, setMyScans] = useState([]);
  
  // Edit এবং Delete এর জন্য State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [scanToDelete, setScanToDelete] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [scanToEdit, setScanToEdit] = useState(null);
  const [newImage, setNewImage] = useState(null);

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
    } else if (role === 'patient') {
      fetchMyScans();
    }
  }, [navigate, token, role]);

  const fetchMyScans = async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8000/api/scans/my-scans/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMyScans(response.data);
    } catch (err) {
      console.error("Failed to fetch scans", err);
    }
  };

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
        headers: { Authorization: `Bearer ${token}` }
      });
      setUploadStatus('Scan uploaded successfully! AI is processing it.');
      setFile(null); 
      fetchMyScans(); // লিস্ট রিফ্রেশ করার জন্য
    } catch (err) {
      setUploadStatus('Failed to upload scan. Please try again.');
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  // ছবির URL ঠিক করার লজিক
  const getImageUrl = (imgPath) => {
    if (!imgPath) return "https://placehold.co/64x64?text=No+Image";
    if (imgPath.startsWith('http')) return imgPath;
    if (!imgPath.startsWith('/')) {
      imgPath = '/' + imgPath;
    }
    return `http://127.0.0.1:8000${imgPath}`;
  };

  // Delete কনফার্মেশন
  const handleDeleteClick = (scan) => {
    setScanToDelete(scan);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    try {
      await axios.delete(`http://127.0.0.1:8000/api/scans/my-scans/${scanToDelete.id}/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchMyScans(); // ডিলিট হওয়ার পর লিস্ট রিফ্রেশ
      setIsDeleteModalOpen(false);
      setScanToDelete(null);
    } catch (err) {
      alert("Failed to delete scan.");
    }
  };

  // Edit লজিক
  const handleEditClick = (scan) => {
    setScanToEdit(scan);
    setIsEditModalOpen(true);
  };

  const handleEditSubmit = async () => {
    if (!newImage) {
      alert("Please select a new image first.");
      return;
    }

    const formData = new FormData();
    formData.append('original_image', newImage);

    try {
      await axios.patch(`http://127.0.0.1:8000/api/scans/my-scans/${scanToEdit.id}/`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      fetchMyScans(); // আপডেট হওয়ার পর লিস্ট রিফ্রেশ
      setIsEditModalOpen(false);
      setNewImage(null);
      setScanToEdit(null);
    } catch (err) {
      alert("Failed to update image.");
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
                <div onClick={() => navigate('/admin/users?role=patient')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer">
                  <h3 className="text-gray-500 text-sm font-medium">Total Patients</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_patients}</p>
                </div>
                <div onClick={() => navigate('/admin/scans?status=all')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer">
                  <h3 className="text-gray-500 text-sm font-medium">Total Scans</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_scans}</p>
                </div>
                <div onClick={() => navigate('/admin/scans?status=pending')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer">
                  <h3 className="text-gray-500 text-sm font-medium">Pending Reviews</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.pending_reviews}</p>
                </div>
                <div onClick={() => navigate('/admin/users?role=radiologist')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer">
                  <h3 className="text-gray-500 text-sm font-medium">Total Radiologists</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_radiologists}</p>
                </div>
                <div onClick={() => navigate('/admin/users?role=doctor')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer">
                  <h3 className="text-gray-500 text-sm font-medium">Total Doctors</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_doctors}</p>
                </div>
                <div onClick={() => navigate('/admin/scans?status=approved')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-sky-200 transition-all cursor-pointer">
                  <h3 className="text-gray-500 text-sm font-medium">Approved Reports</h3>
                  <p className="text-4xl font-bold text-sky-600 mt-2">{stats.approved_reports}</p>
                </div>
              </div>
            ) : (
              <p className="text-gray-400">Loading stats...</p>
            )}
          </div>
        )}

        {/* Patient Upload & History Section */}
        {role === 'patient' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-8">
            
            {/* Left Column: Upload Form */}
            <div>
              <h2 className="text-lg font-semibold text-gray-700 mb-4">Upload New MRI Scan</h2>
              <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
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

            {/* Right Column: Scan History */}
            <div>
              <h2 className="text-lg font-semibold text-gray-700 mb-4">My Scan History</h2>
              <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
                {myScans.length > 0 ? (
                  <div className="space-y-4">
                    {myScans.map((scan) => {
                      const imageUrl = getImageUrl(scan.original_image);
                      
                      return (
                        <div key={scan.id} className="flex items-center space-x-4 p-3 border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors">
                          <img src={imageUrl} alt={`Scan ${scan.id}`} className="w-16 h-16 object-cover rounded-md border border-gray-200" />
                          <div className="flex-1">
                            <p className="font-medium text-gray-900">Scan #{scan.id}</p>
                            <p className="text-sm text-gray-500 capitalize">AI: {scan.analysis?.classification || 'Processing...'}</p>
                            <p className="text-xs text-gray-400 mt-1">{new Date(scan.uploaded_at).toLocaleDateString()}</p>
                          </div>
                          <div className="flex flex-col space-y-2 items-end">
                            {scan.final_report?.status === 'approved' ? (
                              <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-sky-50 text-sky-700 border border-sky-100">Report Ready</span>
                            ) : (
                              <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-yellow-50 text-yellow-700 border border-yellow-100">In Review</span>
                            )}
                            
                            {/* Edit এবং Delete বাটন */}
                            <div className="flex space-x-1">
                              <button 
                                onClick={() => handleEditClick(scan)}
                                className="px-2 py-1 text-xs font-medium text-sky-700 bg-sky-50 border border-sky-200 rounded hover:bg-sky-100"
                              >
                                Edit
                              </button>
                              <button 
                                onClick={() => handleDeleteClick(scan)}
                                className="px-2 py-1 text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded hover:bg-red-100"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-gray-400 text-center py-8">No scans uploaded yet.</p>
                )}
              </div>
            </div>

          </div>
        )}

      </div>

      {/* Delete Confirmation Modal (Popup) */}
      {isDeleteModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">নিশ্চিত করুন</h3>
            <p className="text-gray-600 mb-6">আপনি কি সত্যি তথ্য টি আপনার ডেসবোর্ড থেকে মুছে ফেলতে চান?</p>
            <div className="flex justify-end space-x-3">
              <button 
                onClick={() => setIsDeleteModalOpen(false)} 
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium"
              >
                Cancel
              </button>
              <button 
                onClick={confirmDelete} 
                className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 font-medium"
              >
                OK, Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Image Modal (Popup) */}
      {isEditModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">স্ক্যানের ছবি পরিবর্তন করুন</h3>
            <p className="text-sm text-gray-500 mb-4">Scan ID: #{scanToEdit?.id}</p>
            <input 
              type="file" 
              onChange={(e) => setNewImage(e.target.files[0])} 
              accept="image/*" 
              className="mb-4 w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100"
            />
            <div className="flex justify-end space-x-3 mt-6">
              <button 
                onClick={() => setIsEditModalOpen(false)} 
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium"
              >
                Cancel
              </button>
              <button 
                onClick={handleEditSubmit} 
                className="px-4 py-2 bg-sky-500 text-white rounded-md hover:bg-sky-600 font-medium"
              >
                Upload & Save
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}