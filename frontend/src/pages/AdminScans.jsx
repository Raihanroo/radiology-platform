import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';

export default function AdminScans() {
  const navigate = useNavigate();
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('token');
  
  const [searchParams] = useSearchParams();
  const status = searchParams.get('status');

  // State for Modals
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [scanToDelete, setScanToDelete] = useState(null);
  
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [scanToEdit, setScanToEdit] = useState(null);
  const [newImage, setNewImage] = useState(null);

  // New State for Details Modal
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedDetailScan, setSelectedDetailScan] = useState(null);

  useEffect(() => {
    const fetchScans = async () => {
      try {
        const response = await axios.get(`http://127.0.0.1:8000/api/scans/admin-scans/?status=${status || 'all'}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        if (status === 'approved') {
          setScans(response.data.filter(scan => scan.final_report?.status === 'approved'));
        } else {
          setScans(response.data);
        }
      } catch (err) {
        console.error("Failed to fetch scans", err);
      } finally {
        setLoading(false);
      }
    };
    fetchScans();
  }, [token, status]);

  const getImageUrl = (imgPath) => {
    if (!imgPath) return "https://placehold.co/64x64?text=No+Image";
    if (imgPath.startsWith('http')) return imgPath;
    return `http://127.0.0.1:8000${imgPath}`;
  };

  const handleDeleteClick = (scan) => { setScanToDelete(scan); setIsDeleteModalOpen(true); };

  const confirmDelete = async () => {
    try {
      await axios.delete(`http://127.0.0.1:8000/api/scans/admin-scans/${scanToDelete.id}/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setScans(scans.filter(s => s.id !== scanToDelete.id));
      setIsDeleteModalOpen(false);
      setScanToDelete(null);
    } catch (err) { alert("Failed to delete scan."); }
  };

  const handleEditClick = (scan) => { setScanToEdit(scan); setIsEditModalOpen(true); };

  const handleEditSubmit = async () => {
    if (!newImage) return alert("Please select a new image first.");
    const formData = new FormData();
    formData.append('original_image', newImage);
    try {
      const response = await axios.patch(`http://127.0.0.1:8000/api/scans/admin-scans/${scanToEdit.id}/`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setScans(scans.map(s => s.id === response.data.id ? response.data : s));
      setIsEditModalOpen(false); setNewImage(null); setScanToEdit(null);
      window.location.reload(); 
    } catch (err) { alert("Failed to update image."); }
  };

  const openDetailModal = (scan) => {
    setSelectedDetailScan(scan);
    setIsDetailModalOpen(true);
  };

  const pageTitle = status === 'pending' ? 'Pending Reviews' : status === 'approved' ? 'Approved Reports' : 'All Scans';

  return (
    <div className="min-h-screen bg-slate-50 text-gray-900 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">{pageTitle}</h1>
          <button onClick={() => navigate('/dashboard')} className="px-4 py-2 font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors">
            Back to Dashboard
          </button>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          {loading ? (
            <p className="p-8 text-center text-gray-400">Loading scans...</p>
          ) : scans.length > 0 ? (
            <table className="w-full text-left">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="p-4 font-medium text-gray-500 text-sm">Scan ID</th>
                  <th className="p-4 font-medium text-gray-500 text-sm">MRI Image</th>
                  <th className="p-4 font-medium text-gray-500 text-sm">AI Classification</th>
                  <th className="p-4 font-medium text-gray-500 text-sm">Confidence</th>
                  <th className="p-4 font-medium text-gray-500 text-sm">Status</th>
                  <th className="p-4 font-medium text-gray-500 text-sm text-center">Actions</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((scan) => {
                  const rawScore = scan.analysis?.confidence_score || 0;
                  const displayScore = rawScore > 1 ? rawScore : rawScore * 100;
                  return (
                    <tr key={scan.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors">
                      <td className="p-4 text-gray-400 font-mono text-sm">#{scan.id}</td>
                      <td className="p-4">
                        <img src={getImageUrl(scan.original_image)} alt={`Scan ${scan.id}`} className="w-16 h-16 object-cover rounded-md border border-gray-200 bg-gray-50" onError={(e) => { e.target.src = "https://placehold.co/64x64?text=No+Image"; }} />
                      </td>
                      <td className="p-4">
                        <span className={`px-2.5 py-1 text-xs rounded-full capitalize font-medium ${scan.analysis?.classification === 'notumor' ? 'bg-green-50 text-green-700 border border-green-100' : 'bg-red-50 text-red-700 border border-red-100'}`}>
                          {scan.analysis?.classification || 'N/A'}
                        </span>
                      </td>
                      <td className="p-4 text-gray-600 text-sm">{displayScore > 0 ? `${displayScore.toFixed(2)}%` : 'N/A'}</td>
                      <td className="p-4">
                        {scan.final_report?.status === 'approved' ? (
                          <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-sky-50 text-sky-700 border border-sky-100">Approved</span>
                        ) : scan.radiologist_review ? (
                          <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-blue-50 text-blue-700 border border-blue-100">Reviewed</span>
                        ) : (
                          <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-yellow-50 text-yellow-700 border border-yellow-100">Pending</span>
                        )}
                      </td>
                      <td className="p-4 text-center">
                        <div className="flex space-x-2 justify-center">
                          {/* View Details Button */}
                          <button onClick={() => openDetailModal(scan)} className="px-3 py-1 text-xs font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-md hover:bg-gray-100">
                            View Details
                          </button>
                          <button onClick={() => handleEditClick(scan)} className="px-3 py-1 text-xs font-medium text-sky-700 bg-sky-50 border border-sky-200 rounded-md hover:bg-sky-100">
                            Edit
                          </button>
                          <button onClick={() => handleDeleteClick(scan)} className="px-3 py-1 text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100">
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <p className="p-8 text-center text-gray-500">No scans found.</p>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {isDeleteModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">নিশ্চিত করুন</h3>
            <p className="text-gray-600 mb-6">আপনি কি সত্যি তথ্য টি আপনার ডেসবোর্ড থেকে মুছে ফেলতে চান?</p>
            <div className="flex justify-end space-x-3">
              <button onClick={() => setIsDeleteModalOpen(false)} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium">Cancel</button>
              <button onClick={confirmDelete} className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 font-medium">OK, Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Image Modal */}
      {isEditModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">স্ক্যানের ছবি পরিবর্তন করুন</h3>
            <p className="text-sm text-gray-500 mb-4">Scan ID: #{scanToEdit?.id}</p>
            <input type="file" onChange={(e) => setNewImage(e.target.files[0])} accept="image/*" className="mb-4 w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100" />
            <div className="flex justify-end space-x-3 mt-6">
              <button onClick={() => setIsEditModalOpen(false)} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium">Cancel</button>
              <button onClick={handleEditSubmit} className="px-4 py-2 bg-sky-500 text-white rounded-md hover:bg-sky-600 font-medium">Upload & Save</button>
            </div>
          </div>
        </div>
      )}

      {/* --- NEW: Details View Modal --- */}
      {isDetailModalOpen && selectedDetailScan && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white p-8 rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold text-gray-900">Scan Audit Details #{selectedDetailScan.id}</h3>
              <button onClick={() => setIsDetailModalOpen(false)} className="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
            </div>

            {/* Patient & Image Section */}
            <div className="flex space-x-6 mb-6 p-4 bg-slate-50 rounded-lg border border-gray-200">
              <img src={getImageUrl(selectedDetailScan.original_image)} alt={`Scan ${selectedDetailScan.id}`} className="w-32 h-32 object-cover rounded-md border border-gray-300" />
              <div className="text-sm text-gray-700 space-y-1">
                <p><b>Patient:</b> {selectedDetailScan.patient}</p>
                <p><b>Scan Type:</b> {selectedDetailScan.scan_type || 'N/A'}</p>
                <p><b>Uploaded At:</b> {new Date(selectedDetailScan.uploaded_at).toLocaleString()}</p>
                <p><b>AI Prediction:</b> <span className="capitalize font-medium">{selectedDetailScan.analysis?.classification}</span> ({selectedDetailScan.analysis?.confidence_score ? (selectedDetailScan.analysis.confidence_score > 1 ? selectedDetailScan.analysis.confidence_score : selectedDetailScan.analysis.confidence_score * 100).toFixed(2) : 0}%)</p>
                <p><b>Tumor Area:</b> {selectedDetailScan.analysis?.tumor_area_percentage?.toFixed(2)}%</p>
              </div>
            </div>

            {/* Radiologist Review Section */}
            <div className="mb-6 p-4 border-l-4 border-sky-500 bg-sky-50/50 rounded-r-lg">
              <h4 className="text-md font-semibold text-sky-800 mb-2">🩻 Radiologist Review</h4>
              {selectedDetailScan.radiologist_review ? (
                <div className="text-sm text-gray-700 space-y-1">
                  <p><b>Status:</b> <span className="capitalize">{selectedDetailScan.radiologist_review.status}</span></p>
                  <p><b>Corrected Diagnosis:</b> {selectedDetailScan.radiologist_review.corrected_classification || 'N/A'}</p>
                  <p><b>Observations:</b> {selectedDetailScan.radiologist_review.observations || 'N/A'}</p>
                  <p><b>Reviewed By:</b> {selectedDetailScan.radiologist_review.radiologist} at {new Date(selectedDetailScan.radiologist_review.reviewed_at).toLocaleString()}</p>
                </div>
              ) : (
                <p className="text-sm text-gray-500 italic">Radiologist review pending...</p>
              )}
            </div>

            {/* Doctor Consultation & Final Report Section */}
            <div className="mb-6 p-4 border-l-4 border-green-500 bg-green-50/50 rounded-r-lg">
              <h4 className="text-md font-semibold text-green-800 mb-2">👨‍⚕️ Doctor Consultation & Final Report</h4>
              {selectedDetailScan.doctor_consultation ? (
                <div className="text-sm text-gray-700 space-y-1">
                  <p><b>Clinical Assessment:</b> {selectedDetailScan.doctor_consultation.clinical_assessment || 'N/A'}</p>
                  <p><b>Treatment Recommendation:</b> {selectedDetailScan.doctor_consultation.treatment_recommendation || 'N/A'}</p>
                  <p><b>Consulted By:</b> {selectedDetailScan.doctor_consultation.doctor} at {new Date(selectedDetailScan.doctor_consultation.consulted_at).toLocaleString()}</p>
                  
                  <div className="mt-3 pt-3 border-t border-green-200">
                    <p><b>Final Diagnosis:</b> {selectedDetailScan.final_report?.final_diagnosis || 'N/A'}</p>
                    <p><b>Report Summary:</b> {selectedDetailScan.final_report?.summary || 'N/A'}</p>
                    <p>
                      <b>Report Status:</b> 
                      <span className={`ml-2 px-2 py-0.5 text-xs font-medium rounded-full ${selectedDetailScan.final_report?.status === 'approved' ? 'bg-sky-100 text-sky-800' : 'bg-yellow-100 text-yellow-800'}`}>
                        {selectedDetailScan.final_report?.status || 'N/A'}
                      </span>
                    </p>
                    {selectedDetailScan.final_report?.status === 'approved' ? (
                      <p className="text-green-600 font-medium mt-1">✅ Patient has received this report.</p>
                    ) : (
                      <p className="text-yellow-600 font-medium mt-1">⏳ Report is in draft. Patient cannot see it yet.</p>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-500 italic">Doctor consultation pending...</p>
              )}
            </div>

            <div className="flex justify-end pt-4">
              <button onClick={() => setIsDetailModalOpen(false)} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium">Close</button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}