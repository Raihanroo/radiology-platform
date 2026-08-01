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
  const [reviewQueue, setReviewQueue] = useState([]);
  const [consultQueue, setConsultQueue] = useState([]);
  
  // রেডিওলজিস্ট রিভিউ মডালের জন্য State
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [selectedScan, setSelectedScan] = useState(null);
  const [reviewData, setReviewData] = useState({ status: 'approved', observations: '', corrected_classification: '' });
  const [reviewError, setReviewError] = useState('');

  // ডাক্তার কনসালটেশন মডালের জন্য State
  const [isConsultModalOpen, setIsConsultModalOpen] = useState(false);
  const [selectedConsultScan, setSelectedConsultScan] = useState(null);
  const [consultData, setConsultData] = useState({ clinical_assessment: '', treatment_recommendation: '', summary: '' });
  const [consultError, setConsultError] = useState('');

  const username = localStorage.getItem('username');
  const role = localStorage.getItem('role');
  const token = localStorage.getItem('token');

  useEffect(() => {
    if (!token) { navigate('/'); return; }
    if (role === 'admin' || role === 'super_admin') fetchStats();
    else if (role === 'patient') fetchMyScans();
    else if (role === 'radiologist') fetchReviewQueue();
    else if (role === 'doctor') fetchConsultQueue();
  }, [navigate, token, role]);

  const fetchStats = async () => {
    try { const res = await axios.get('http://127.0.0.1:8000/api/scans/admin-stats/', { headers: { Authorization: `Bearer ${token}` } }); setStats(res.data); } 
    catch (err) { console.error(err); }
  };
  const fetchMyScans = async () => {
    try { const res = await axios.get('http://127.0.0.1:8000/api/scans/my-scans/', { headers: { Authorization: `Bearer ${token}` } }); setMyScans(res.data); } 
    catch (err) { console.error(err); }
  };
  const fetchReviewQueue = async () => {
    try { const res = await axios.get('http://127.0.0.1:8000/api/scans/review-queue/', { headers: { Authorization: `Bearer ${token}` } }); setReviewQueue(res.data); } 
    catch (err) { console.error(err); }
  };
  const fetchConsultQueue = async () => {
    try { const res = await axios.get('http://127.0.0.1:8000/api/scans/consultation-queue/', { headers: { Authorization: `Bearer ${token}` } }); setConsultQueue(res.data); } 
    catch (err) { console.error(err); }
  };

  const handleLogout = () => { localStorage.clear(); navigate('/'); };
  const handleFileChange = (e) => setFile(e.target.files[0]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return alert("Please select an MRI image first.");
    setUploading(true); setUploadStatus('');
    const formData = new FormData(); formData.append('original_image', file);
    try {
      await axios.post('http://127.0.0.1:8000/api/scans/analyze/', formData, { headers: { Authorization: `Bearer ${token}` } });
      setUploadStatus('Scan uploaded successfully! AI is processing it.'); setFile(null); fetchMyScans();
    } catch (err) { setUploadStatus('Failed to upload scan.'); } 
    finally { setUploading(false); }
  };

  const getImageUrl = (imgPath) => {
    if (!imgPath) return "https://placehold.co/64x64?text=No+Image";
    if (imgPath.startsWith('http')) return imgPath;
    if (!imgPath.startsWith('/')) imgPath = '/' + imgPath;
    return `http://127.0.0.1:8000${imgPath}`;
  };

  const handleReviewSubmit = async (e) => {
    e.preventDefault(); setReviewError('');
    try {
      await axios.post(`http://127.0.0.1:8000/api/scans/${selectedScan.id}/review/`, reviewData, { headers: { Authorization: `Bearer ${token}` } });
      setIsReviewModalOpen(false); setSelectedScan(null); setReviewData({ status: 'approved', observations: '', corrected_classification: '' }); fetchReviewQueue();
    } catch (err) { setReviewError("Failed to submit review."); }
  };
  const openReviewModal = (scan) => {
    setSelectedScan(scan); setReviewData({ status: 'approved', observations: '', corrected_classification: scan.analysis?.classification || '' }); setIsReviewModalOpen(true);
  };

  // ডাক্তার কনসালটেশন ও রিপোর্ট অ্যাপ্রুভ সাবমিট
  const handleConsultSubmit = async (e) => {
    e.preventDefault(); setConsultError('');
    try {
      await axios.post(`http://127.0.0.1:8000/api/scans/${selectedConsultScan.id}/consult/`, {
        clinical_assessment: consultData.clinical_assessment,
        treatment_recommendation: consultData.treatment_recommendation
      }, { headers: { Authorization: `Bearer ${token}` } });
      
      await axios.post(`http://127.0.0.1:8000/api/scans/${selectedConsultScan.id}/generate-report/`, {
        summary: consultData.summary
      }, { headers: { Authorization: `Bearer ${token}` } });

      await axios.post(`http://127.0.0.1:8000/api/scans/${selectedConsultScan.id}/approve-report/`, {}, { headers: { Authorization: `Bearer ${token}` } });

      setIsConsultModalOpen(false); 
      setSelectedConsultScan(null); 
      setConsultData({ clinical_assessment: '', treatment_recommendation: '', summary: '' }); 
      fetchConsultQueue();
    } catch (err) { 
      setConsultError("Failed to process consultation."); 
      console.error("Consultation Error:", err.response?.data);
    }
  };
  const openConsultModal = (scan) => {
    setSelectedConsultScan(scan); setConsultData({ clinical_assessment: '', treatment_recommendation: '', summary: '' }); setIsConsultModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-gray-900 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">Welcome, {username}!</h1>
            <p className="text-gray-500 mt-1 text-sm">Role: <span className="capitalize text-sky-600 font-semibold border border-sky-100 bg-sky-50 px-2 py-0.5 rounded-full text-xs">{role}</span></p>
          </div>
          <div className="flex space-x-3">
            {(role === 'admin' || role === 'super_admin') && (
              <button onClick={() => navigate('/admin/users')} className="px-4 py-2 font-medium text-white bg-sky-500 rounded-md hover:bg-sky-600 transition-colors">Manage Users</button>
            )}
            <button onClick={handleLogout} className="px-4 py-2 font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors">Logout</button>
          </div>
        </div>

        {/* Admin Stats */}
        {(role === 'admin' || role === 'super_admin') && (
          <div className="mt-8">
            <h2 className="text-lg font-semibold text-gray-700 mb-4">System Overview</h2>
            {stats ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div onClick={() => navigate('/admin/users?role=patient')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md cursor-pointer"><h3 className="text-gray-500 text-sm">Total Patients</h3><p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_patients}</p></div>
                <div onClick={() => navigate('/admin/scans?status=all')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md cursor-pointer"><h3 className="text-gray-500 text-sm">Total Scans</h3><p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_scans}</p></div>
                <div onClick={() => navigate('/admin/scans?status=pending')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md cursor-pointer"><h3 className="text-gray-500 text-sm">Pending Reviews</h3><p className="text-4xl font-bold text-sky-600 mt-2">{stats.pending_reviews}</p></div>
                <div onClick={() => navigate('/admin/users?role=radiologist')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md cursor-pointer"><h3 className="text-gray-500 text-sm">Total Radiologists</h3><p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_radiologists}</p></div>
                <div onClick={() => navigate('/admin/users?role=doctor')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md cursor-pointer"><h3 className="text-gray-500 text-sm">Total Doctors</h3><p className="text-4xl font-bold text-sky-600 mt-2">{stats.total_doctors}</p></div>
                <div onClick={() => navigate('/admin/scans?status=approved')} className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md cursor-pointer"><h3 className="text-gray-500 text-sm">Approved Reports</h3><p className="text-4xl font-bold text-sky-600 mt-2">{stats.approved_reports}</p></div>
              </div>
            ) : <p className="text-gray-400">Loading stats...</p>}
          </div>
        )}

        {/* Patient Dashboard */}
        {role === 'patient' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-8">
            <div>
              <h2 className="text-lg font-semibold text-gray-700 mb-4">Upload New MRI Scan</h2>
              <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
                <form onSubmit={handleUpload} className="space-y-5">
                  <div className="flex flex-col items-center justify-center w-full">
                    <label htmlFor="dropzone-file" className="flex flex-col items-center justify-center w-full h-44 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <svg className="w-10 h-10 mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                        <p className="mb-2 text-sm text-gray-500"><span className="font-semibold text-sky-600">Click to upload</span> or drag and drop</p>
                        <p className="text-xs text-gray-400">JPG, PNG, TIF up to 10MB</p>
                      </div>
                      <input id="dropzone-file" type="file" className="hidden" onChange={handleFileChange} accept="image/*" />
                    </label>
                  </div>
                  {file && <p className="text-sm text-gray-600 text-center">Selected file: <span className="font-medium text-sky-600">{file.name}</span></p>}
                  {uploadStatus && <div className={`p-3 text-sm rounded-md text-center ${uploadStatus.includes('successfully') ? 'bg-green-50 text-green-700 border border-green-100' : 'bg-red-50 text-red-700 border border-red-100'}`}>{uploadStatus}</div>}
                  <button type="submit" disabled={uploading || !file} className="w-full px-4 py-3 font-semibold text-white bg-sky-500 rounded-md hover:bg-sky-600 disabled:bg-sky-300">{uploading ? 'Uploading...' : 'Upload & Analyze'}</button>
                </form>
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-700 mb-4">My Scan History</h2>
              <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
                {myScans.length > 0 ? (
                  <div className="space-y-4">
                    {myScans.map((scan) => (
                      <div key={scan.id} className="flex items-center space-x-4 p-3 border border-gray-100 rounded-lg hover:bg-gray-50">
                        <img src={getImageUrl(scan.original_image)} alt={`Scan ${scan.id}`} className="w-16 h-16 object-cover rounded-md border" />
                        <div className="flex-1">
                          <p className="font-medium text-gray-900">Scan #{scan.id}</p>
                          <p className="text-sm text-gray-500 capitalize">AI: {scan.analysis?.classification || 'Processing...'}</p>
                          <p className="text-xs text-gray-400 mt-1">{new Date(scan.uploaded_at).toLocaleDateString()}</p>
                        </div>
                        <div>{scan.final_report?.status === 'approved' ? <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-sky-50 text-sky-700 border border-sky-100">Report Ready</span> : <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-yellow-50 text-yellow-700 border border-yellow-100">In Review</span>}</div>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-gray-400 text-center py-8">No scans uploaded yet.</p>}
              </div>
            </div>
          </div>
        )}

        {/* Radiologist Dashboard */}
        {role === 'radiologist' && (
          <div className="mt-8">
            <h2 className="text-lg font-semibold text-gray-700 mb-4">Pending Review Queue</h2>
            <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
              {reviewQueue.length > 0 ? (
                <div className="space-y-4">
                  {reviewQueue.map((scan) => (
                    <div key={scan.id} className="flex items-center space-x-4 p-3 border border-gray-100 rounded-lg hover:bg-gray-50">
                      <img src={getImageUrl(scan.original_image)} alt={`Scan ${scan.id}`} className="w-20 h-20 object-cover rounded-md border" />
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">Scan #{scan.id} <span className="text-xs text-gray-400 ml-2">{scan.patient}</span></p>
                        <p className="text-sm text-gray-500 capitalize">AI Prediction: {scan.analysis?.classification} ({scan.analysis?.confidence_score ? (scan.analysis.confidence_score > 1 ? scan.analysis.confidence_score : scan.analysis.confidence_score * 100).toFixed(2) : 0}%)</p>
                        <p className="text-xs text-red-500 mt-1">Segmentation Area: {scan.analysis?.tumor_area_percentage ? scan.analysis.tumor_area_percentage.toFixed(2) : 0}%</p>
                      </div>
                      <button onClick={() => openReviewModal(scan)} className="px-4 py-2 font-medium text-white bg-sky-500 rounded-md hover:bg-sky-600">Review Now</button>
                    </div>
                  ))}
                </div>
              ) : <p className="text-gray-400 text-center py-8">No pending reviews. Great job!</p>}
            </div>
          </div>
        )}

        {/* Doctor Dashboard */}
        {role === 'doctor' && (
          <div className="mt-8">
            <h2 className="text-lg font-semibold text-gray-700 mb-4">Pending Consultation Queue</h2>
            <div className="p-6 bg-white rounded-lg border border-gray-200 shadow-sm">
              {consultQueue.length > 0 ? (
                <div className="space-y-4">
                  {consultQueue.map((scan) => (
                    <div key={scan.id} className="flex items-center space-x-4 p-3 border border-gray-100 rounded-lg hover:bg-gray-50">
                      <img src={getImageUrl(scan.original_image)} alt={`Scan ${scan.id}`} className="w-20 h-20 object-cover rounded-md border" />
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">Scan #{scan.id} <span className="text-xs text-gray-400 ml-2">Patient: {scan.patient}</span></p>
                        <p className="text-sm text-gray-500 capitalize">Final Diagnosis: {scan.radiologist_review?.corrected_classification || scan.analysis?.classification}</p>
                        <p className="text-xs text-gray-400 mt-1">Radiologist Notes: {scan.radiologist_review?.observations || 'N/A'}</p>
                      </div>
                      <button onClick={() => openConsultModal(scan)} className="px-4 py-2 font-medium text-white bg-sky-500 rounded-md hover:bg-sky-600">Consult & Report</button>
                    </div>
                  ))}
                </div>
              ) : <p className="text-gray-400 text-center py-8">No pending consultations.</p>}
            </div>
          </div>
        )}
      </div>

      {/* Radiologist Review Modal */}
      {isReviewModalOpen && selectedScan && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-lg w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Review Scan #{selectedScan.id}</h3>
            <div className="mb-4 p-3 bg-gray-50 rounded-md border border-gray-200">
              <p className="text-sm text-gray-600"><b>Patient:</b> {selectedScan.patient}</p>
              <p className="text-sm text-gray-600"><b>AI Classification:</b> {selectedScan.analysis?.classification}</p>
              <p className="text-sm text-gray-600"><b>Tumor Area:</b> {selectedScan.analysis?.tumor_area_percentage?.toFixed(2)}%</p>
            </div>
            {reviewError && <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-100 rounded-md mb-4">{reviewError}</div>}
            <form onSubmit={handleReviewSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Review Status</label>
                <select value={reviewData.status} onChange={(e) => setReviewData({ ...reviewData, status: e.target.value })} className="w-full px-3 py-2 mt-1 bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500">
                  <option value="approved">Approve AI Result</option>
                  <option value="modified">Modify Classification</option>
                  <option value="rejected">Reject Scan (Invalid)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Corrected Classification</label>
                <input type="text" value={reviewData.corrected_classification} onChange={(e) => setReviewData({ ...reviewData, corrected_classification: e.target.value })} className="w-full px-3 py-2 mt-1 bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500" placeholder="e.g., glioma, notumor" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Observations / Notes</label>
                <textarea rows="3" value={reviewData.observations} onChange={(e) => setReviewData({ ...reviewData, observations: e.target.value })} className="w-full px-3 py-2 mt-1 bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500" placeholder="Write clinical observations..." required></textarea>
              </div>
              <div className="flex justify-end space-x-3 pt-4">
                <button type="button" onClick={() => setIsReviewModalOpen(false)} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-sky-500 text-white rounded-md hover:bg-sky-600 font-medium">Submit Review</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Doctor Consultation Modal (বিস্তারিত তথ্য সহ আপডেট করা হয়েছে) */}
      {isConsultModalOpen && selectedConsultScan && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Consult & Approve Report #{selectedConsultScan.id}</h3>
            
            {/* রেডিওলজিস্ট এবং AI এর বিস্তারিত তথ্য */}
            <div className="mb-4 p-4 bg-gray-50 rounded-md border border-gray-200">
              <div className="flex space-x-4">
                <img src={getImageUrl(selectedConsultScan.original_image)} alt={`Scan ${selectedConsultScan.id}`} className="w-28 h-28 object-cover rounded-md border border-gray-300" />
                <div className="text-sm text-gray-700 flex-1 space-y-1">
                  <p><b>Patient:</b> {selectedConsultScan.patient}</p>
                  <p><b>AI Prediction:</b> <span className="capitalize">{selectedConsultScan.analysis?.classification}</span> ({selectedConsultScan.analysis?.confidence_score ? (selectedConsultScan.analysis.confidence_score > 1 ? selectedConsultScan.analysis.confidence_score : selectedConsultScan.analysis.confidence_score * 100).toFixed(2) : 0}%)</p>
                  <p><b>Segmentation Area:</b> {selectedConsultScan.analysis?.tumor_area_percentage?.toFixed(2)}%</p>
                  <hr className="my-2 border-gray-200" />
                  <p className="capitalize"><b>Radiologist Status:</b> {selectedConsultScan.radiologist_review?.status || 'N/A'}</p>
                  <p><b>Radiologist Diagnosis:</b> {selectedConsultScan.radiologist_review?.corrected_classification || 'N/A'}</p>
                  <p><b>Radiologist Notes:</b> {selectedConsultScan.radiologist_review?.observations || 'N/A'}</p>
                </div>
              </div>
            </div>

            {consultError && <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-100 rounded-md mb-4">{consultError}</div>}
            
            <form onSubmit={handleConsultSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Clinical Assessment</label>
                <textarea rows="2" value={consultData.clinical_assessment} onChange={(e) => setConsultData({ ...consultData, clinical_assessment: e.target.value })} className="w-full px-3 py-2 mt-1 bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500" placeholder="Your clinical assessment based on radiologist notes..." required></textarea>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Treatment Recommendation</label>
                <textarea rows="2" value={consultData.treatment_recommendation} onChange={(e) => setConsultData({ ...consultData, treatment_recommendation: e.target.value })} className="w-full px-3 py-2 mt-1 bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500" placeholder="Treatment recommendation / advice..." required></textarea>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Final Report Summary</label>
                <textarea rows="3" value={consultData.summary} onChange={(e) => setConsultData({ ...consultData, summary: e.target.value })} className="w-full px-3 py-2 mt-1 bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500" placeholder="Write the final detailed report summary for the patient..." required></textarea>
              </div>
              <div className="flex justify-end space-x-3 pt-4">
                <button type="button" onClick={() => setIsConsultModalOpen(false)} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 font-medium">Submit & Approve Report</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}