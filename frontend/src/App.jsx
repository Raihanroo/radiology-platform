import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import AdminUsers from './pages/AdminUsers'; // নতুন ইম্পোর্ট
import AdminScans from './pages/AdminScans';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/admin/scans" element={<AdminScans />} /> {/* নতুন রাউট */}
        </Routes>
      </div>
    </Router>
  );
}

export default App;