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

   useEffect(() => {
    const fetchScans = async () => {
      try {
        const response = await axios.get(`http://127.0.0.1:8000/api/scans/admin-scans/?status=${status || 'all'}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        // যদি অ্যাপ্রুভড রিপোর্ট চাওয়া হয়, তবে শুধু approved স্ক্যানগুলো দেখাবে
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

  // টাইটেল ডাইনামিকভাবে পরিবর্তন হবে
  const pageTitle = status === 'pending' 
    ? 'Pending Reviews' 
    : status === 'approved' 
      ? 'Approved Reports' 
      : 'All Scans';

  return (
    <div className="min-h-screen bg-slate-50 text-gray-900 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">{pageTitle}</h1>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
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
                </tr>
              </thead>
              <tbody>
                {scans.map((scan) => {
                  // ছবির URL ঠিক করার লজিক
                  const imageUrl = scan.original_image?.startsWith('http')
                    ? scan.original_image
                    : `http://127.0.0.1:8000${scan.original_image}`;

                  // কনফিডেন্স স্কোর ঠিক করার লজিক
                  const rawScore = scan.analysis?.confidence_score || 0;
                  const displayScore = rawScore > 1 ? rawScore : rawScore * 100;

                  return (
                    <tr key={scan.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors">
                      <td className="p-4 text-gray-400 font-mono text-sm">#{scan.id}</td>
                      <td className="p-4">
                        <img 
                          src={imageUrl} 
                          alt={`Scan ${scan.id}`} 
                          className="w-16 h-16 object-cover rounded-md border border-gray-200 bg-gray-50"
                        />
                      </td>
                      <td className="p-4">
                        <span className={`px-2.5 py-1 text-xs rounded-full capitalize font-medium ${
                          scan.analysis?.classification === 'notumor' 
                            ? 'bg-green-50 text-green-700 border border-green-100' 
                            : 'bg-red-50 text-red-700 border border-red-100'
                        }`}>
                          {scan.analysis?.classification || 'N/A'}
                        </span>
                      </td>
                      <td className="p-4 text-gray-600 text-sm">
                        {displayScore > 0 ? `${displayScore.toFixed(2)}%` : 'N/A'}
                      </td>
                      <td className="p-4">
                        {scan.final_report?.status === 'approved' ? (
                           <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-sky-50 text-sky-700 border border-sky-100">Approved</span>
                        ) : scan.radiologist_review ? (
                           <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-blue-50 text-blue-700 border border-blue-100">Reviewed</span>
                        ) : (
                           <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-yellow-50 text-yellow-700 border border-yellow-100">Pending</span>
                        )}
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
    </div>
  );
}