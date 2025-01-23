import React from 'react';

function Home() {
    return (
        <div>
            <h1>Home</h1>
            <p>Welcome to the home page!</p>
            <p hx-get="backend/user/{id}">NAME</p>
        </div>
    );
}