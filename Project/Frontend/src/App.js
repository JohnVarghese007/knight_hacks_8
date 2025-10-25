import React from 'react';
import './App.css';
import FileUpload from './components/FileUpload';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>RxVerify</h1>
        <p>Upload your prescription for verification</p>
      </header>
      <main>
        <FileUpload />
      </main>
    </div>
  );
}

export default App;