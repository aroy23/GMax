import { createRoot } from 'react-dom/client';

const GoogleLogo = () => (
  <svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    <path d="M1 1h22v22H1z" fill="none"/>
  </svg>
);

const Popup = () => {
  return (
    <div style={{ width: '300px', padding: '16px' }}>
      <h1>GMax</h1>
      <p>Sign in to get started!</p>
      
      <button 
        onClick={() => {
          fetch('http://localhost:8000/auth/url?redirect_uri=http://localhost:8000/auth/callback')
            .then(response => response.json())
            .then(data => {
              // Open auth in popup
              window.open(data.auth_url, 'oauth', 'width=600,height=700');
            })
            .catch(error => console.error('Error:', error));
        }}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          width: '100%',
          padding: '12px',
          marginTop: '16px',
          background: 'white',
          border: '1px solid #dadce0',
          borderRadius: '8px',
          color: '#3c4043',
          fontSize: '14px',
          fontWeight: 500,
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1)',
        }}
        onMouseOver={(e) => {
          e.currentTarget.style.background = '#f8f9fa';
          e.currentTarget.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.1)';
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.background = 'white';
          e.currentTarget.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.1)';
        }}
      >
        <div style={{ width: '18px', height: '18px', marginBottom: '6px' }}>
          <GoogleLogo />
        </div>
        Sign in with Google
      </button>
    </div>
  );
};

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<Popup />);
} 