import { createRoot } from 'react-dom/client';

const Popup = () => {
  return (
    <div style={{ width: '300px', padding: '16px' }}>
      <h1>My Chrome Extension</h1>
      <p>Welcome to your new Chrome extension!</p>
    </div>
  );
};

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<Popup />);
} 