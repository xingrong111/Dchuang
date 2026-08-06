export const setItem = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.error('Storage setItem error:', error);
  }
};

export const getItem = (key) => {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  } catch (error) {
    console.error('Storage getItem error:', error);
    return null;
  }
};

export const removeItem = (key) => {
  try {
    localStorage.removeItem(key);
  } catch (error) {
    console.error('Storage removeItem error:', error);
  }
};

export const clear = () => {
  try {
    localStorage.clear();
  } catch (error) {
    console.error('Storage clear error:', error);
  }
};