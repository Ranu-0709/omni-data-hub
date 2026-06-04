import { useEffect, useState } from 'react';

export default function AdminHome() {
  const [franchises, setFranchises] = useState([]);

  useEffect(() => {
    // Fetching the onboard dates from your backend API
    fetch('http://34.100.159.85:8000/franchises')
      .then(res => res.json())
      .then(data => setFranchises(data))
      .catch(err => console.error("Error fetching data:", err));
  }, []);

return (
  <div style={{ padding: '40px', fontFamily: '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif', backgroundColor: '#f9f9f9', minHeight: '100vh' }}>
    <header style={{ borderBottom: '3px solid #0078d4', marginBottom: '30px', paddingBottom: '10px' }}>
      <h1 style={{ color: '#333', margin: '0' }}>Omni Data Hub | <span style={{ fontWeight: '300' }}>Control Room</span></h1>
      <p style={{ color: '#666' }}>Real-time monitoring for your Google Cloud Data Infrastructure.</p>
    </header>

    <div style={{ backgroundColor: '#fff', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ backgroundColor: '#0078d4', color: '#fff', textAlign: 'left' }}>
            <th style={{ padding: '15px' }}>Franchise Name</th>
            <th style={{ padding: '15px' }}>Onboard Date</th>
            <th style={{ padding: '15px' }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {franchises.map((f, i) => (
            <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: '15px', fontWeight: 'bold' }}>Franchise {f.name}</td>
              <td style={{ padding: '15px', color: '#555' }}>{new Date(f.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</td>
              <td style={{ padding: '15px' }}>
                <span style={{ padding: '4px 12px', borderRadius: '20px', fontSize: '12px', backgroundColor: '#d1e7dd', color: '#0f5132' }}>Active</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);
}



// export default function AdminHome() {
//   return (
//     <div>
//       <h1>Omni Data Hub - Control Room</h1>
//       <p>Heavy data visibility. This runs safely inside your Google Cloud server.</p>
//     </div>
//   )
// }
