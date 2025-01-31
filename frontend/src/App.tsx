import React from 'react';
import './App.css';
import Head from './components/head';
import Navbar from './components/navbar';
import Header from './components/header';
import Footer from './components/footer';


function App() {
  return (
    <div className="App">
      <Head />
      <Header />
      <Navbar />
      <Footer />
    </div>
  );
}

export default App;
