import React, { useState } from 'react';
import { useWallet } from './contexts/WalletContext';
import Spinner from './Spinner';
import { toast } from 'react-hot-toast';

function Auth() {
  const { authLoading, signUp, confirmSignUp, logIn } = useWallet();

  const [mode, setMode] = useState('signup');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmationCode, setConfirmationCode] = useState('');

  const handleSubmit = async (e) => {
  e.preventDefault();
  if (!email || !password) {
    toast.error("Email and password are required.");
    return;
  }

  if (mode === 'signup') {
    // --- Sign Up Logic ---
    try {
      await signUp(email, password);
      toast.success('Account created! Please log in.');
      setMode('login'); // <-- Go straight to login
      setPassword(''); // Clear password field
    } catch (err) {
      toast.error(`Sign up failed: ${err.message}`);
    }
  } else if (mode === 'login') {
    // --- Log In Logic ---
    try {
      await logIn(email, password);
      // Success is handled by the context
    } catch (err) {
      // The UserNotConfirmedException error will no longer happen
      toast.error(`Login failed: ${err.message}`);
    }
  }
};

  return (
    <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-6 mb-8 shadow-sm">
      <h2 className="text-xl font-semibold text-neutral-700 mb-6 text-center">
        {mode === 'login' ? 'Log In' : 'Sign Up'}
      </h2>
      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label htmlFor="email" className="block text-sm font-medium text-neutral-700">Email</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full p-2 border border-neutral-300 rounded-md shadow-sm focus:ring-primary-blue focus:border-primary-blue"
            required
          />
        </div>
        <div className="mb-4">
          <label htmlFor="password" className="block text-sm font-medium text-neutral-700">Password</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min 8 chars, 1 upper, 1 lower, 1 number"
            className="mt-1 block w-full p-2 border border-neutral-300 rounded-md shadow-sm focus:ring-primary-blue focus:border-primary-blue"
            required
          />
        </div>
        <button
          type="submit"
          disabled={authLoading}
          className="w-full px-4 py-2 bg-primary-blue text-white rounded-md hover:bg-primary-blue-dark focus:outline-none focus:ring-2 focus:ring-primary-blue focus:ring-offset-2 disabled:bg-primary-blue-light"
        >
          {authLoading ? <Spinner mini={true} /> : (mode === 'login' ? 'Log In' : 'Sign Up')}
        </button>
      </form>
      <div className="mt-4 text-center">
        <button
          onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}
          className="text-sm text-primary-blue hover:underline focus:outline-none"
        >
          {mode === 'login' ? 'Need an account? Sign Up' : 'Have an account? Log In'}
        </button>
      </div>
    </div>
  );
}

export default Auth;