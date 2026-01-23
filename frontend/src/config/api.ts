// API Configuration
const isDevelopment = process.env.NODE_ENV === 'development' || !process.env.NODE_ENV;

export const API_CONFIG = {
  BASE_URL: isDevelopment 
    ? 'http://localhost:8000'
    : '',
  
  // API Endpoints
  ENDPOINTS: {
    ANALYZE: '/analyze',
    JOBS: '/jobs',
    JOB_DETAIL: (jobId: string) => `/job/${jobId}`,
    JOB_ANALYSIS: (jobId: string) => `/job/${jobId}/complete-analysis`,
    JOB_FEATURES: (jobId: string) => `/job/${jobId}/features`,
    JOB_CFG: (jobId: string) => `/job/${jobId}/cfg`,
    JOB_CFG_IMAGE: (jobId: string) => `/job/${jobId}/cfg/image`,
    EXTRACT_FEATURES: (jobId: string) => `/job/${jobId}/extract-features`,
    FS_SCAN: (jobId: string) => ` /job/${jobId}/fs-scan`,
  }
};

export const API_URL = API_CONFIG.BASE_URL;