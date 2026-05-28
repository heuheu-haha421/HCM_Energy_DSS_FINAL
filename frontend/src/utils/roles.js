export const isUser = (user) => user?.role === 'user'
export const isAdmin = (user) => user?.role === 'admin'
export const isDev = (user) => user?.role === 'dev'
export const isAdminOrDev = (user) => isAdmin(user) || isDev(user)

export const canMutate = (user) => isAdminOrDev(user)

// Destructive dev actions stay hidden until the backend exposes an enabled config.
export const canDevDelete = () => false
