// frontend/src/cognitoConfig.js

// Get the User Pool ID and Client ID from your .env files
const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID;
const userPoolClientId = import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID;

if (!userPoolId || !userPoolClientId) {
  console.error("Cognito environment variables are missing!");
}

export const cognitoConfig = {
  UserPoolId: userPoolId,
  ClientId: userPoolClientId,
};