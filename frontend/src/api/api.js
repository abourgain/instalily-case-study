export const getAIMessage = async (userQuery) => {
  console.log("User Query: ", userQuery);

  const message = {
    role: "assistant",
    content: "Connect your backend here....",
  };

  return message;
};
