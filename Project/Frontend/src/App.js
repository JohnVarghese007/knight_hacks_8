import React from 'react';

function Navbar() {
  return (
<<<<<<< HEAD
    <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
      <ul style={{
        listStyle: 'none',
        margin: 0,
        padding: 0,
        display: 'flex',
        gap: '48px',
        alignItems: 'center'
      }}>
        <li>
           <a href="/" style={{
             color: '#eaf6ff',
             textDecoration: 'none',
             padding: '16px',
             fontWeight: '600',
             fontSize: '1.2rem',
             background: 'transparent',
             transition: 'color .15s ease'
           }}
           onMouseEnter={(e) => {
             e.target.style.color = '#1e90ff';
           }}
           onMouseLeave={(e) => {
             e.target.style.color = '#eaf6ff';
           }}>
            Home
          </a>
        </li>
        <li>
           <a href="/signup" style={{
             color: '#eaf6ff',
             textDecoration: 'none',
             padding: '16px',
             fontWeight: '600',
             fontSize: '1.3rem',
             background: 'transparent',
             transition: 'color .15s ease'
           }}
           onMouseEnter={(e) => {
             e.target.style.color = '#1e90ff';
           }}
           onMouseLeave={(e) => {
             e.target.style.color = '#eaf6ff';
           }}>
            Sign Up
          </a>
        </li>
        <li>
           <a href="/login" style={{
             color: '#eaf6ff',
             textDecoration: 'none',
             padding: '16px',
             fontWeight: '600',
             fontSize: '1.3rem',
             background: 'transparent',
             transition: 'color .15s ease'
           }}
           onMouseEnter={(e) => {
             e.target.style.color = '#1e90ff';
           }}
           onMouseLeave={(e) => {
             e.target.style.color = '#eaf6ff';
           }}>
            Login
          </a>
        </li>
      </ul>
    </nav>
  );
}

function HomePage() {
  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      {/* Hero Section */}
      <section style={{
        textAlign: 'center',
        padding: '60px 20px',
        marginBottom: '40px'
      }}>
        <h1 style={{
          fontSize: '3rem',
          fontWeight: '700',
          marginBottom: '20px',
          background: 'linear-gradient(135deg, #1e90ff 0%, #00d4ff 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>
          Welcome to MedVerify
        </h1>
        <p style={{
          fontSize: '1.25rem',
          color: '#9fb8d6',
          maxWidth: '600px',
          margin: '0 auto 30px',
          lineHeight: '1.6'
        }}>
          Your trusted platform for secure medical prescription verification and validation
        </p>
        <button style={{
          background: '#1e90ff',
          color: '#042033',
          border: 'none',
          padding: '14px 32px',
          borderRadius: '8px',
          cursor: 'pointer',
          fontWeight: '600',
          fontSize: '1.1rem',
          marginTop: '10px'
        }}>
          Get Started
        </button>
      </section>

      {/* Features Section */}
      <section style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '24px',
        marginBottom: '40px'
      }}>
        <div style={{
          background: 'linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01))',
          border: '1px solid rgba(255,255,255,0.04)',
          boxShadow: '0 6px 18px rgba(2,10,20,0.6)',
          padding: '28px',
          borderRadius: '12px',
          textAlign: 'center'
        }}>
          <div style={{
            fontSize: '2.5rem',
            marginBottom: '16px'
          }}>🔒</div>
          <h3 style={{
            fontSize: '1.3rem',
            marginBottom: '12px',
            color: '#eaf6ff'
          }}>Secure</h3>
          <p style={{
            color: '#9fb8d6',
            lineHeight: '1.5'
          }}>
            End-to-end encryption ensures your medical data stays private and protected
          </p>
        </div>

        <div style={{
          background: 'linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01))',
          border: '1px solid rgba(255,255,255,0.04)',
          boxShadow: '0 6px 18px rgba(2,10,20,0.6)',
          padding: '28px',
          borderRadius: '12px',
          textAlign: 'center'
        }}>
          <div style={{
            fontSize: '2.5rem',
            marginBottom: '16px'
          }}>⚡</div>
          <h3 style={{
            fontSize: '1.3rem',
            marginBottom: '12px',
            color: '#eaf6ff'
          }}>Fast</h3>
          <p style={{
            color: '#9fb8d6',
            lineHeight: '1.5'
          }}>
            Quick verification process gets you results in minutes, not hours
          </p>
        </div>

        <div style={{
          background: 'linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01))',
          border: '1px solid rgba(255,255,255,0.04)',
          boxShadow: '0 6px 18px rgba(2,10,20,0.6)',
          padding: '28px',
          borderRadius: '12px',
          textAlign: 'center'
        }}>
          <div style={{
            fontSize: '2.5rem',
            marginBottom: '16px'
          }}>✓</div>
          <h3 style={{
            fontSize: '1.3rem',
            marginBottom: '12px',
            color: '#eaf6ff'
          }}>Accurate</h3>
          <p style={{
            color: '#9fb8d6',
            lineHeight: '1.5'
          }}>
            Advanced verification technology ensures precision and reliability
          </p>
        </div>
      </section>

      {/* CTA Section */}
      <section style={{
        background: 'linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01))',
        border: '1px solid rgba(255,255,255,0.04)',
        boxShadow: '0 6px 18px rgba(2,10,20,0.6)',
        padding: '40px',
        borderRadius: '12px',
        textAlign: 'center',
        marginTop: '40px'
      }}>
        <h2 style={{
          fontSize: '2rem',
          marginBottom: '16px',
          color: '#eaf6ff'
        }}>
          Ready to verify your prescriptions?
        </h2>
        <p style={{
          color: '#9fb8d6',
          fontSize: '1.1rem',
          marginBottom: '24px'
        }}>
          Join thousands of users who trust MedVerify for their medical verification needs
        </p>
        <button style={{
          background: '#1e90ff',
          color: '#042033',
          border: 'none',
          padding: '12px 28px',
          borderRadius: '8px',
          cursor: 'pointer',
          fontWeight: '600',
          fontSize: '1rem',
          marginRight: '12px'
        }}>
          Sign Up Now
        </button>
        <button style={{
          background: 'transparent',
          color: '#1e90ff',
          border: '2px solid #1e90ff',
          padding: '12px 28px',
          borderRadius: '8px',
          cursor: 'pointer',
          fontWeight: '600',
          fontSize: '1rem'
        }}>
          Learn More
        </button>
      </section>
=======
    <div className="App">
      <header className="App-header">
        <h3>RxVerify</h3>
        <Navbar />
      </header>
      <FileUpload />
      <main>
      </main>
>>>>>>> f86ceee9c0fb4d36a044dc354bd5c9d47f7b0141
    </div>
  );
}

<<<<<<< HEAD
export default function App() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'stretch',
      background: 'linear-gradient(180deg, #071630 0%, #021423 100%)',
      color: '#eaf6ff',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial'
    }}>
      <header style={{
        background: '#0f3250',
        minHeight: '84px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        fontSize: 'calc(12px + 0.4vmin)',
        color: '#eaf6ff',
        padding: '16px 24px',
      boxShadow: '0 2px 8px rgba(2,10,20,0.6)'
    }}>
        <Navbar />
        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
        </div>
      </header>
      <main style={{
        padding: '28px',
        maxWidth: '980px',
        margin: '24px auto',
        width: '100%'
      }}>
        <HomePage />
      </main>
    </div>
  );
}
=======
function Navbar() {

    return (
        <nav className="navbar">
            <ul>
                <li><a href="/">Home</a></li>
                <li><a href="/Sign Up">Sign Up</a></li>
                <li><a href="/login">Login</a></li>
            </ul>
        </nav>
    );
}


export default App;
>>>>>>> f86ceee9c0fb4d36a044dc354bd5c9d47f7b0141
