import LearningWorkspace from './components/LearningWorkspace.jsx';
import DeveloperPortal from './components/DeveloperPortal.jsx';

export default function App() {
  if (window.location.pathname === '/developer' || window.location.pathname.startsWith('/developer/')) {
    return <DeveloperPortal />;
  }
  return <LearningWorkspace />;
}
