import React, { useState } from 'react';
import './FileUpload.css';

function FileUpload() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
    
    // Create preview
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch('http://localhost:5000/upload', {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div className="file-upload">
      <form onSubmit={handleSubmit}>
        <div className="upload-container">
          <input
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            id="file-input"
            className="file-input"
          />
          <label htmlFor="file-input" className="file-label">
            Choose a file or drag it here
          </label>
        </div>
        
        {preview && (
          <div className="preview">
            <img src={preview} alt="Preview" />
          </div>
        )}
        
        <button type="submit" className="submit-button" disabled={!selectedFile}>
          Upload and Verify
        </button>
      </form>

      {result && (
        <div className="result">
          <h3>Results:</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default FileUpload;