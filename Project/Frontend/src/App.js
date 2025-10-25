import React from 'react';
import './App.css';
import FileUpload from './components/FileUpload';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h3>RxVerify</h3>
        <Navbar />
      </header>
      <FileUpload />
      <main>
      </main>
    </div>
  );
}

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
