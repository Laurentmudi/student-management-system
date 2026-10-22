import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import { Loading } from "./components/ui.jsx";
import Login from "./pages/Login.jsx";
import Verify from "./pages/Verify.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Students from "./pages/Students.jsx";
import StudentForm from "./pages/StudentForm.jsx";
import StudentDetail from "./pages/StudentDetail.jsx";
import Courses from "./pages/Courses.jsx";
import Trainers from "./pages/Trainers.jsx";
import Payments from "./pages/Payments.jsx";
import Attendance from "./pages/Attendance.jsx";
import ProgressPage from "./pages/ProgressPage.jsx";
import Certificates from "./pages/Certificates.jsx";
import Reports from "./pages/Reports.jsx";
import Notifications from "./pages/Notifications.jsx";
import Settings from "./pages/Settings.jsx";
import Logs from "./pages/Logs.jsx";
import Account from "./pages/Account.jsx";
import SearchPage from "./pages/SearchPage.jsx";

function Guard({ admin, children }) {
  const { user, loading, isAdmin } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && !isAdmin) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/verify/:kind/:number" element={<Verify />} />
      <Route element={<Guard><Layout /></Guard>}>
        <Route index element={<Dashboard />} />
        <Route path="students" element={<Students />} />
        <Route path="students/new" element={<Guard admin><StudentForm /></Guard>} />
        <Route path="students/:id/edit" element={<Guard admin><StudentForm /></Guard>} />
        <Route path="students/:id" element={<StudentDetail />} />
        <Route path="attendance" element={<Attendance />} />
        <Route path="progress" element={<ProgressPage />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="account" element={<Account />} />
        <Route path="courses" element={<Guard admin><Courses /></Guard>} />
        <Route path="trainers" element={<Guard admin><Trainers /></Guard>} />
        <Route path="payments" element={<Guard admin><Payments /></Guard>} />
        <Route path="certificates" element={<Guard admin><Certificates /></Guard>} />
        <Route path="reports" element={<Guard admin><Reports /></Guard>} />
        <Route path="logs" element={<Guard admin><Logs /></Guard>} />
        <Route path="settings" element={<Guard admin><Settings /></Guard>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
