import React from 'react';
import { Link } from 'react-router';


export default function Navbar() {
    return (
        <div>
            <nav className="navbar navbar-default">
                <div className="container-fluid">
                    <ul className="nav navbar-nav">
                        <li><Link to='/'>Home</Link></li>
                    </ul>
                </div>
            </nav>
        </div>
    )
}
